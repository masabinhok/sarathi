# ioe

A LangGraph chatbot (Ollama / `qwen2.5:7b`) with a FastAPI backend and a Next.js chat UI.

```
src/ioe/graph.py   LangGraph graph + checkpointer (shared by CLI and API)
src/ioe/rag.py     docs/ loading, chunking, Chroma index, retrieval
src/ioe/api.py     FastAPI app, SSE token streaming
src/ioe/main.py    terminal chat loop
docs/              English source documents indexed for retrieval
web/               Next.js frontend
```

## Running

Ollama must be running with `qwen2.5:7b` and `bge-m3` pulled.

Build the retrieval index first (and again after any change under `docs/`):

```bash
uv run ioe-index
```

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

## Retrieval

The graph runs `rewrite_query -> retrieve -> chat_node`. The rewrite step condenses a
follow-up ("what about the fees?") into a standalone query using recent history, since
a bare follow-up embeds poorly on its own. Retrieval pulls the top `TOP_K` chunks from
Chroma above a cosine relevance floor, and the answer node cites the title and year of
whatever it used.

`bge-m3` embeds the chunks. It is multilingual, so English queries do match Nepali
source text -- documents are translated to English for the generator's benefit, not the
retriever's. See `docs/README.md` for the document format.

With no index built, or when nothing clears the relevance floor, retrieval yields no
context and the bot says it lacks the document rather than answering from memory.
