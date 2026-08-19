# ioe

A LangGraph chatbot (Ollama / `qwen2.5:7b`) with a FastAPI backend and a Next.js chat UI.

```
src/ioe/graph.py   LangGraph graph + checkpointer (shared by CLI and API)
src/ioe/api.py     FastAPI app, SSE token streaming
src/ioe/main.py    terminal chat loop
web/               Next.js frontend
```

## Running

Ollama must be running with `qwen2.5:7b` and `bge-m3` pulled.

Backend (port 8000):

```bash
uv run uvicorn ioe.api:app --reload --port 8000
```

Frontend (port 3000):

```bash
cd web && npm run dev
```

Then open http://localhost:3000. The terminal chat loop still works via `uv run ioe`.

## API

| Method | Path                     | Description                              |
| ------ | ------------------------ | ---------------------------------------- |
| GET    | `/api/health`            | Status + active model                    |
| POST   | `/api/chat`              | `{message, thread_id?}` → SSE token stream |
| GET    | `/api/history/{thread}`  | Replay a thread's messages               |
| POST   | `/api/thread`            | Mint a new thread id                     |

Conversation state lives in LangGraph's `InMemorySaver`, keyed by `thread_id`, so it
resets when the backend restarts. The frontend keeps its `thread_id` in `localStorage`
and replays history on load.
