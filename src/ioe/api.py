import asyncio
import json
import os
import re
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from ioe import notices as notices_mod
from ioe import threads as threads_mod
from ioe.dates import today_payload
from ioe.deadlines import as_payload as deadlines_payload
from ioe.graph import TEXT_MODEL, get_chatbot
from ioe.rag import DOCS_DIR, EMB_MODEL, build_index, load_documents

# Read .env before anything reads os.environ, so ADMIN_TOKEN can live in a file
# rather than the shell that happens to launch uvicorn.
load_dotenv()

app = FastAPI(title="sarathi api")

# The browser -- not the container -- is what calls this API, so the allowed origin is
# wherever the frontend is published. Override when it is not on the default port.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class Source(BaseModel):
    """A document the answer was drawn from, as retrieval recorded it."""

    title: str
    year: str | None = None
    url: str | None = None
    file: str
    sections: list[str] = []


class Message(BaseModel):
    role: str
    content: str
    sources: list[Source] | None = None


class Thread(BaseModel):
    """One conversation as the history sidebar lists it."""

    thread_id: str
    title: str
    created_at: str
    updated_at: str
    turns: int


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _finished_sources(thread_id: str) -> list[dict] | None:
    """Citations for the answer just written, read back off the checkpoint.

    They ride on the finished message rather than in the token stream, since retrieval
    knows its documents before the first token and the student reads them after the last.
    A failure here costs the citations only -- never the answer the student already has.
    """
    try:
        chatbot = await get_chatbot()
        state = await chatbot.aget_state(_config(thread_id))
    except Exception:  # noqa: BLE001 - an uncited answer still beats a truncated stream
        return None
    messages = state.values.get("messages", []) if state.values else []
    return messages[-1].additional_kwargs.get("sources") if messages else None


# How long a generated title may keep the student waiting once their answer is complete.
# Past this the opening question stands in, and the model's version is dropped rather
# than applied late -- a sidebar row that renames itself after you have read it is worse
# than one that was always the question you asked.
TITLE_TIMEOUT = 8.0


async def _stream(message: str, thread_id: str, client_id: str) -> AsyncIterator[str]:
    yield _sse("start", {"thread_id": thread_id})

    # Naming happens on the first turn only, and the provisional name is written before
    # the answer starts: if the connection drops mid-stream the conversation is still in
    # the sidebar, under the question that opened it.
    naming = not await threads_mod.exists(thread_id)
    title = threads_mod.fallback_title(message)
    await threads_mod.record(thread_id, client_id, title)
    if naming:
        yield _sse("title", {"thread_id": thread_id, "title": title})
        # Started here, read after the answer: the title is a second call to a 7B model
        # that is already busy, and it must not delay the first token.
        titling = asyncio.create_task(
            asyncio.to_thread(threads_mod.make_title, message)
        )

    try:
        chatbot = await get_chatbot()
        stream = chatbot.astream(
            {"messages": [HumanMessage(content=message)]},
            _config(thread_id),
            stream_mode="messages",
        )
        async for chunk, metadata in stream:
            # The graph also calls the model to rewrite follow-up queries for retrieval;
            # only the answer node's tokens belong in the UI.
            if metadata.get("langgraph_node") != "chat_node":
                continue
            text = chunk.content
            if text:
                yield _sse("token", {"text": text})
    except Exception as exc:  # noqa: BLE001 - any failure must reach the UI, not stall the stream
        yield _sse("error", {"message": str(exc)})

    sources = await _finished_sources(thread_id)
    if sources:
        yield _sse("sources", {"sources": sources})

    if naming:
        better = await _await_title(titling)
        if better and better != title:
            await threads_mod.retitle(thread_id, better)
            yield _sse("title", {"thread_id": thread_id, "title": better})

    yield _sse("done", {"thread_id": thread_id})


async def _await_title(task: asyncio.Task) -> str | None:
    """Collect the generated title if it arrived in time, and give up on it if not."""
    try:
        # A timeout cancels the task, which is the intent: nothing downstream is waiting
        # on a title that arrived after the student had already read the answer.
        return await asyncio.wait_for(task, TITLE_TIMEOUT)
    except Exception:  # noqa: BLE001 - the opening question already titles the thread
        return None


@app.get("/api/health")
async def health() -> dict:
    """Liveness plus the corpus size, which the UI shows so a student can see what the
    answers are drawn from. Counts only -- no document contents, so no auth needed."""
    chunks = await asyncio.to_thread(load_documents)
    return {
        "status": "ok",
        "model": TEXT_MODEL,
        "embedding_model": EMB_MODEL,
        "documents": len({chunk.metadata.get("file") for chunk in chunks}),
        "chunks": len(chunks),
    }


@app.post("/api/thread")
async def new_thread() -> dict:
    return {"thread_id": uuid.uuid4().hex}


@app.get("/api/threads")
async def list_threads(x_client_id: str = Header(default="")) -> list[Thread]:
    """The conversations this browser started, newest first.

    Scoped to the caller's own id rather than returning the whole table: there are no
    accounts here, but a shared deployment would otherwise show every visitor everyone
    else's questions, and those questions name real candidates and their results.
    """
    return [Thread(**row) for row in await threads_mod.listing(x_client_id)]


@app.delete("/api/threads/{thread_id}")
async def delete_thread(thread_id: str) -> dict:
    """Forget a conversation: its index row and every checkpointed message."""
    removed = await threads_mod.forget(thread_id)
    chatbot = await get_chatbot()
    await chatbot.checkpointer.adelete_thread(thread_id)
    if not removed:
        raise HTTPException(404, "no such conversation")
    return {"thread_id": thread_id, "deleted": True}


@app.get("/api/history/{thread_id}")
async def history(thread_id: str) -> list[Message]:
    chatbot = await get_chatbot()
    state = await chatbot.aget_state(_config(thread_id))
    messages = state.values.get("messages", []) if state.values else []
    out: list[Message] = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            out.append(Message(role="user", content=msg.content))
        elif isinstance(msg, AIMessage) and msg.content:
            out.append(
                Message(
                    role="assistant",
                    content=msg.content,
                    sources=msg.additional_kwargs.get("sources"),
                )
            )
    return out


@app.post("/api/chat")
async def chat(
    req: ChatRequest, x_client_id: str = Header(default="")
) -> StreamingResponse:
    thread_id = req.thread_id or uuid.uuid4().hex
    return StreamingResponse(
        _stream(req.message, thread_id, x_client_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --- notices and deadlines -------------------------------------------------------------


@app.get("/api/today")
async def today() -> dict:
    return today_payload()


@app.get("/api/notices")
async def notices() -> dict:
    """Cached notices scraped from IOE/TU/campus sites. Never scrapes on request."""
    return notices_mod.load()


@app.get("/api/deadlines")
async def deadlines() -> dict:
    return deadlines_payload()


# --- admin -----------------------------------------------------------------------------

UPLOAD_DIR = DOCS_DIR / "translated"
SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+\.md$")
MAX_UPLOAD_BYTES = 2_000_000


def require_admin(x_admin_token: str = Header(default="")) -> None:
    """Gate admin routes on a shared secret.

    An unset ADMIN_TOKEN denies everything rather than allowing everything: a missing
    config should never be the thing that opens up write access.
    """
    expected = os.environ.get("ADMIN_TOKEN", "")
    if not expected:
        raise HTTPException(503, "ADMIN_TOKEN is not configured on the server")
    if x_admin_token != expected:
        raise HTTPException(401, "invalid admin token")


@app.get("/api/admin/status", dependencies=[Depends(require_admin)])
async def admin_status() -> dict:
    chunks = await asyncio.to_thread(load_documents)
    per_file: dict[str, int] = {}
    for chunk in chunks:
        name = chunk.metadata.get("file", "?")
        per_file[name] = per_file.get(name, 0) + 1

    files = []
    for path in sorted(UPLOAD_DIR.glob("*.md")):
        if path.name.startswith("_"):
            continue
        files.append(
            {
                "name": path.name,
                "bytes": path.stat().st_size,
                "chunks": per_file.get(path.name, 0),
            }
        )
    return {
        "documents": files,
        "total_chunks": len(chunks),
        "text_model": TEXT_MODEL,
        "embedding_model": EMB_MODEL,
    }


@app.post("/api/admin/documents", dependencies=[Depends(require_admin)])
async def upload_document(file: Annotated[UploadFile, File()]) -> dict:
    raw_name = file.filename or ""
    # Reject a path-bearing name outright rather than silently saving its basename:
    # taking the basename is safe, but writing a file under a name the caller did not
    # send is worse than telling them no.
    if raw_name != Path(raw_name).name or not SAFE_NAME.match(raw_name):
        raise HTTPException(400, "filename must be a plain ASCII .md name with no path")
    name = raw_name

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "file is larger than 2 MB")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, "file must be UTF-8 text") from None
    if not text.lstrip().startswith("---"):
        raise HTTPException(
            400, "file must start with YAML frontmatter (see docs/README.md)"
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target = UPLOAD_DIR / name
    replaced = target.exists()
    target.write_text(text, encoding="utf-8")
    return {
        "name": name,
        "bytes": len(raw),
        "replaced": replaced,
        "reindex_required": True,
    }


@app.delete("/api/admin/documents/{name}", dependencies=[Depends(require_admin)])
async def delete_document(name: str) -> dict:
    safe = Path(name).name
    if not SAFE_NAME.match(safe):
        raise HTTPException(400, "invalid document name")
    target = UPLOAD_DIR / safe
    if not target.exists():
        raise HTTPException(404, "no such document")
    target.unlink()
    return {"name": safe, "deleted": True, "reindex_required": True}


@app.post("/api/admin/reindex", dependencies=[Depends(require_admin)])
async def reindex() -> dict:
    count = await asyncio.to_thread(build_index)
    return {"chunks": count}


@app.post("/api/admin/notices/refresh", dependencies=[Depends(require_admin)])
async def refresh_notices() -> dict:
    payload = await asyncio.to_thread(notices_mod.refresh)
    return {
        "updated_at": payload["updated_at"],
        "count": len(payload["notices"]),
        "sources": payload["sources"],
    }
