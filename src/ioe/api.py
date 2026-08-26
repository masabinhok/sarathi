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
from ioe.graph import TEXT_MODEL, english_only_preface, get_chatbot
from ioe.rag import (
    DOCS_DIR,
    EMB_MODEL,
    build_index,
    load_documents,
    refresh_notice_index,
)

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


async def _finished_turn(thread_id: str) -> tuple[str, list[dict] | None]:
    """The refusal and the citations for the turn just taken, off the checkpoint.

    Both ride on the finished state rather than in the token stream. Citations do
    because retrieval knows its documents before the first token while the student reads
    them after the last; the refusal does because graph.deflect writes it without calling
    the model, so there are no tokens for it to arrive as. A failure here costs the
    citations -- never the answer the student already has.
    """
    try:
        chatbot = await get_chatbot()
        state = await chatbot.aget_state(_config(thread_id))
    except Exception:  # noqa: BLE001 - an uncited answer still beats a truncated stream
        return "", None
    values = state.values or {}
    messages = values.get("messages", [])
    sources = messages[-1].additional_kwargs.get("sources") if messages else None
    return values.get("refusal") or "", sources


# The one node whose tokens are the answer. The graph runs the model more than once a
# turn -- the planner picks tools, memory.summarize writes the rolling summary -- and
# every one of those calls streams chunks past here carrying its own node name. Filtering
# on this name is what makes the token stream the answer and nothing else; the planner's
# TAG_NOSTREAM is a second layer, not the guarantee.
FINAL_NODE = "answer"

# How long a generated title may keep the student waiting once their answer is complete.
# Past this the opening question stands in, and the model's version is dropped rather
# than applied late -- a sidebar row that renames itself after you have read it is worse
# than one that was always the question you asked.
TITLE_TIMEOUT = 8.0


async def _stream(message: str, thread_id: str, client_id: str) -> AsyncIterator[str]:
    yield _sse("start", {"thread_id": thread_id})

    # Someone is here and asking, so make sure the notice feed is not a day old. This
    # returns immediately; the fetch it may start runs behind the answer.
    await _freshen_notices()

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
        # The app's own words, before the model's. See graph.english_only_preface.
        preface = english_only_preface(message)
        if preface:
            yield _sse("token", {"text": preface})

        async for chunk, metadata in stream:
            if metadata.get("langgraph_node") != FINAL_NODE:
                continue
            # The answer node invokes graph.model, which has no tools bound, so a tool
            # call cannot be generated here at all. Checked anyway: the cost is an
            # attribute lookup per chunk, and the failure it guards against is raw
            # tool-call JSON rendered to a student as if it were the answer.
            if getattr(chunk, "tool_calls", None) or getattr(
                chunk, "tool_call_chunks", None
            ):
                continue
            text = chunk.content
            if text:
                yield _sse("token", {"text": text})
    except Exception as exc:  # noqa: BLE001 - any failure must reach the UI, not stall the stream
        yield _sse("error", {"message": str(exc)})

    refusal, sources = await _finished_turn(thread_id)
    # graph.deflect turned the question away, so no answer was generated and no token
    # has been sent. The student still needs to be told, in the app's own words. This
    # path is narrower than the scope guard it replaces -- one task-substitution
    # detector, not a classifier -- but it is not gone, so neither is this branch.
    if refusal:
        yield _sse("token", {"text": refusal})
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


# How stale the notice cache may be before a question triggers a fetch of its own. The
# cron that refreshes it daily is the floor, not the only trigger: during admission week a
# list published at 2pm should not be invisible to a student asking at 4pm.
NOTICE_MAX_AGE = 20 * 60

# One at a time, and never awaited by the turn that started it. Scraping six sites takes
# seconds, and a student waiting on an answer should not be paying for it -- the fetch
# lands in time for the next question, or for the next person to ask this one.
_freshening: asyncio.Task | None = None


def _refresh_notices() -> dict:
    """Scrape the feed, then bring the indexed notice records in line with it."""
    notices_mod.refresh()
    refresh_notice_index()
    # Re-read rather than use what refresh returned: indexing writes the record ids back.
    return notices_mod.load()


async def _freshen_notices() -> None:
    """Start a background refresh if the cache has gone stale and none is running."""
    global _freshening
    try:
        if _freshening and not _freshening.done():
            return
        if notices_mod.age_seconds() < NOTICE_MAX_AGE:
            return
        _freshening = asyncio.create_task(asyncio.to_thread(_refresh_notices))
    except Exception:  # noqa: BLE001 - a stale notice feed must never fail an answer
        _freshening = None


# --- notices and deadlines -------------------------------------------------------------


@app.get("/api/today")
async def today() -> dict:
    return today_payload()


@app.get("/api/notices")
async def notices(limit: int = 0) -> dict:
    """Cached notices from the IOE boards and campus admission portals.

    Never scrapes on request -- the feed is refreshed in the background by _freshen_notices
    and by the admin route. limit trims the list for callers that show a handful, so the
    rail stops paying for seven sources' worth of notices to render five of them; 0 means
    the whole index, which is what /notices wants.
    """
    payload = notices_mod.load()
    if limit > 0:
        payload = {**payload, "notices": payload.get("notices", [])[:limit]}
    return payload


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
    payload = await asyncio.to_thread(_refresh_notices)
    return {
        "updated_at": payload["updated_at"],
        "count": len(payload["notices"]),
        "indexed": len(payload.get("indexed_ids") or []),
        "sources": payload["sources"],
    }
