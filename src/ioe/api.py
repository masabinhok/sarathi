import json
import uuid
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from ioe.graph import TEXT_MODEL, chatbot

app = FastAPI(title="ioe chat api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class Message(BaseModel):
    role: str
    content: str


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _stream(message: str, thread_id: str) -> AsyncIterator[str]:
    yield _sse("start", {"thread_id": thread_id})
    try:
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
    yield _sse("done", {"thread_id": thread_id})


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "model": TEXT_MODEL}


@app.post("/api/thread")
async def new_thread() -> dict:
    return {"thread_id": uuid.uuid4().hex}


@app.get("/api/history/{thread_id}")
async def history(thread_id: str) -> list[Message]:
    state = await chatbot.aget_state(_config(thread_id))
    messages = state.values.get("messages", []) if state.values else []
    out: list[Message] = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            out.append(Message(role="user", content=msg.content))
        elif isinstance(msg, AIMessage) and msg.content:
            out.append(Message(role="assistant", content=msg.content))
    return out


@app.post("/api/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    thread_id = req.thread_id or uuid.uuid4().hex
    return StreamingResponse(
        _stream(req.message, thread_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
