# Sarathi

**सारथी** — the one who steers you where you are going.

A retrieval-backed assistant for students applying to the Institute of Engineering (IOE),
Tribhuvan University, Nepal. It answers questions about the BE/BArch entrance examination
and admission process from official IOE notices, looks up published entrance results by
form number or merit rank, and tracks admission deadlines in both Bikram Sambat and
Gregorian calendars.

Everything runs locally. No API keys, no cloud inference — the language and embedding
models run on your own machine through Ollama.

```
src/ioe/graph.py      LangGraph graph: query rewrite -> retrieve -> lookup -> answer
src/ioe/rag.py        document loading, chunking, Chroma index, retrieval + reranking
src/ioe/results.py    exact lookup over the published entrance pass list
src/ioe/fees.py       fee totals worked out from the published fee tables
src/ioe/priority.py   last year's Pulchowk cutoffs, simulated from the priority list
src/ioe/dates.py      current date in BS/AD, Bikram Sambat conversion
src/ioe/deadlines.py  dated obligations mined from the indexed documents
src/ioe/notices.py    scraper for the IOE boards and campus admission portals
src/ioe/extract.py    notice PDF text extraction, Preeti decoding, review queue
src/ioe/api.py        FastAPI app: SSE chat streaming, notices, deadlines, admin
src/ioe/main.py       terminal chat loop
docs/                 source PDFs, English translations, extracted notices, lookup tables
web/                  Next.js frontend
```

## Requirements

| Tool   | Version tested | Notes                                        |
| ------ | -------------- | -------------------------------------------- |
| Python | 3.12.3         | 3.12 or newer is required                    |
| uv     | 0.12.1         | manages the virtualenv and dependencies      |
| Node   | 22.23.1        | for the Next.js frontend                     |
| npm    | 10.9.8         | ships with Node                              |
| Ollama | 0.32.6         | runs both models locally                     |

You need roughly **6 GB of free disk** for the two Ollama models and about **8 GB of RAM**
to run the 7B model comfortably.

Only Ollama is strictly required if you use Docker — see [Quick start with Docker](#quick-start-with-docker), which supplies Python and Node itself.

## Quick start with Docker

If you would rather not install Python, Node, and their dependencies, one command builds
and runs both services:

```bash
docker compose up --build
```

The frontend lands on <http://localhost:3000> and the backend on <http://localhost:8000>.
The first run also builds the vector index and scrapes the notice board inside the
container, which takes a few minutes; later runs reuse both from named volumes.

**Ollama stays on the host.** The compose file points the backend at your existing
install rather than containerising it — that is where the models you already pulled live,
and on a GPU machine it is the copy with the drivers. On Linux, Ollama listens on
`127.0.0.1` only, which no container can reach, so bind it to all interfaces once:

```bash
sudo systemctl edit ollama
# in the editor that opens, add:
#   [Service]
#   Environment="OLLAMA_HOST=0.0.0.0"
sudo systemctl restart ollama
```

Docker Desktop on macOS and Windows needs no such change. To skip it on Linux and run
Ollama in a container instead:

```bash
docker compose -f compose.yaml -f compose.ollama.yaml up --build
```

That variant downloads both models (~6 GB) into a volume on first start, so prefer the
default if you already have them.

### What the containers share with the host

| Path      | Kind         | Why                                                      |
| --------- | ------------ | -------------------------------------------------------- |
| `docs/`   | bind mount   | documents uploaded through `/admin` land in the repo      |
| `.chroma` | named volume | the vector index, rebuilt only when it is missing         |
| `.cache`  | named volume | the scraped notice board                                  |
| `.env`    | env file     | supplies `ADMIN_TOKEN`; absent means admin routes are 503 |

Ports come from `API_PORT` and `WEB_PORT` (8000 and 3000 by default). The frontend calls
the API from the *browser*, not from inside the network, so `NEXT_PUBLIC_API_URL` is baked
into the image at build time — change `API_PORT` and you have to rebuild with `--build`.

Useful follow-ups:

```bash
docker compose exec api ioe-index      # reindex after editing docs/
docker compose exec api ioe-notices    # re-scrape the notice board
docker compose exec api ioe-extract    # queue new notice PDFs for review in /admin
docker compose logs -f api             # follow backend logs
docker compose down                    # stop; add -v to discard index and notices too
```

The rest of this README covers running the stack directly on your machine, which is the
better setup if you are changing the code.

## Setup

### 1. Install the prerequisites

If you do not already have them:

```bash
# uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

Install Node 22 or newer from https://nodejs.org or your package manager.

### 2. Clone and install Python dependencies

```bash
git clone <your-repo-url> ioe
cd ioe
uv sync
```

`uv sync` creates `.venv/` and installs everything from `uv.lock`. You do not need to
create a virtualenv yourself, and you do not need to activate it — every command below
uses `uv run`, which uses `.venv` automatically.

If you prefer an activated shell (so you can call `python`, `uvicorn`, and `pytest`
directly without the `uv run` prefix):

```bash
source .venv/bin/activate
```

### 3. Pull the Ollama models

```bash
ollama pull qwen2.5:7b     # ~4.7 GB, generates the answers
ollama pull bge-m3         # ~1.2 GB, embeds documents and questions
```

`bge-m3` is multilingual, which is what lets English questions match Nepali source text.

Make sure the Ollama server is running before you start the backend:

```bash
ollama serve      # not needed if Ollama runs as a system service
ollama list       # should show both models
```

### 4. Build the retrieval index

```bash
uv run ioe-index
```

This chunks every Markdown file under `docs/translated/` and embeds it into a local
Chroma store at `.chroma/`. It takes a minute or two on first run. Expect output like:

```
indexed 189 chunks from /path/to/ioe/docs
```

**The bot cannot answer document questions until this runs.** Re-run it after adding or
editing anything in `docs/translated/`.

### 5. Fetch the notice board (optional)

```bash
uv run ioe-notices
```

Scrapes recent admission and entrance notices into `.cache/notices.json` from seven
sources: the IOE Entrance Exam Board, the central admission portal, and the Pulchowk,
Thapathali, Pashchimanchal, Purwanchal and Chitwan campuses. Tribhuvan University's
general feeds are deliberately not among them. The app reads only that cache and never
scrapes on request, so it works offline and stays fast. Skipping this leaves the notices
section empty; nothing else is affected.

### 6. Extract notice text (optional)

```bash
uv run ioe-extract
```

Downloads the PDFs behind the newest notices, pulls their text out with `pdftotext`, and
writes each one to `.cache/pending/` for review. **Nothing is indexed by this command.**
Approving an extraction is a person: open `/admin`, read the text, and press approve,
which writes it to `docs/notices/` — then rebuild the index to publish it.

The split is deliberate. `docs/README.md` explains that the failure mode which matters in
this corpus is numeric drift, and machine extraction does not change that; it changes what
a reviewer starts from. Extractions decoded from the Preeti legacy font are flagged in the
admin list and carry a warning in the file, because that text was decoded rather than read
and a wrong digit in it looks exactly like a right one.

### 6. Install frontend dependencies

```bash
cd web
npm install
cd ..
```

## Running

Three processes. Ollama must be running for the other two to work.

```bash
# terminal 1 - Ollama (skip if it runs as a system service)
ollama serve

# terminal 2 - backend on port 8000
uv run uvicorn ioe.api:app --reload --port 8000

# terminal 3 - frontend on port 3000
cd web && npm run dev
```

Open http://localhost:3000.

A terminal-only chat loop is also available, with no frontend needed:

```bash
uv run ioe
```

### Checking it works

```bash
curl localhost:8000/api/health
# {"status":"ok","model":"qwen2.5:7b"}
```

If the browser reports **"CORS request did not succeed"** with a null status code, the
backend is not running — a refused connection produces no response and therefore no CORS
headers. Check `/api/health` before suspecting the CORS configuration.

## Configuration

Create a `.env` file in the repository root:

```bash
ADMIN_TOKEN=choose-a-long-random-string
```

`ADMIN_TOKEN` guards the admin endpoints (document upload, reindex, notice refresh). If
it is unset, every admin route returns 503 — a missing token denies access rather than
granting it, so an unconfigured deployment is never accidentally open.

Two further variables matter only when the backend is not on the same host as its
dependencies, and Docker sets both for you:

| Variable          | Default                                            | Purpose                          |
| ----------------- | -------------------------------------------------- | -------------------------------- |
| `OLLAMA_BASE_URL` | `http://localhost:11434`                           | where Ollama is reachable        |
| `CORS_ORIGINS`    | `http://localhost:3000,http://127.0.0.1:3000`      | browser origins allowed to call  |

The frontend reads `NEXT_PUBLIC_API_URL` and falls back to `http://localhost:8000`. Set
it in `web/.env.local` if the backend runs elsewhere.

## API

| Method | Path                          | Auth  | Description                                |
| ------ | ----------------------------- | ----- | ------------------------------------------ |
| GET    | `/api/health`                 | —     | Status and active model                    |
| POST   | `/api/chat`                   | —     | `{message, thread_id?}` → SSE token stream |
| GET    | `/api/history/{thread_id}`    | —     | Replay a thread's messages                 |
| POST   | `/api/thread`                 | —     | Mint a new thread id                       |
| GET    | `/api/today`                  | —     | Today's date in BS and AD                  |
| GET    | `/api/notices`                | —     | Cached notices from IOE/TU/campus sites    |
| GET    | `/api/deadlines`              | —     | Deadlines mined from indexed documents     |
| GET    | `/api/admin/status`           | token | Indexed documents and chunk counts         |
| POST   | `/api/admin/documents`        | token | Upload a translated `.md` file             |
| DELETE | `/api/admin/documents/{name}` | token | Remove a document                          |
| POST   | `/api/admin/reindex`          | token | Rebuild the vector store                   |
| POST   | `/api/admin/notices/refresh`  | token | Re-scrape the notice boards                |

Admin routes take the token in an `X-Admin-Token` header:

```bash
curl -H "X-Admin-Token: $ADMIN_TOKEN" localhost:8000/api/admin/status
```

Conversation state lives in LangGraph's `InMemorySaver`, keyed by `thread_id`, so it
resets when the backend restarts. The frontend keeps its `thread_id` in `localStorage`
and replays history on load.

## How answers are produced

The graph runs `rewrite_query → retrieve → lookup_result → chat_node`.

**Query rewriting** condenses a follow-up ("what about the fees?") into a standalone
query using recent history, because a bare follow-up embeds poorly on its own.

**Retrieval** over-fetches `TOP_K * 2` chunks from Chroma, re-ranks them, and trims to
`TOP_K`. Documents tagged `audience: foreign` in their frontmatter are demoted unless the
question mentions a foreign applicant, since most students are Nepali nationals. Chunks
below a cosine relevance floor are dropped; when nothing clears it, the bot says it lacks
the document rather than answering from memory.

**Pass list lookup** is separate from retrieval. The published result list is a
7,179-row table, and vector search over names and form numbers returns near-noise, so
`lookup_result` scans the raw question for a form number or merit rank and reads the CSV
in `docs/data/` directly. It works in both directions: a form number resolves to a rank,
and a rank resolves to the candidate holding it. It reads the raw question rather than
the rewritten one so the model cannot mangle a digit.

**Dates** are injected on every turn. The model has no reliable sense of today's date and
is poor at Bikram Sambat arithmetic, so the current date is supplied in both calendars —
anchored to `Asia/Kathmandu`, not the server's timezone — and every BS date in the
question or retrieved text is pre-resolved to AD with an offset from today ("8 days ago",
"in 43 days"). The model reads those off rather than calculating.

## Adding documents

See `docs/README.md` for the document format, the frontmatter contract, and translation
guidance. In short:

- `docs/downloads/` holds the original PDFs, for provenance. Never indexed.
- `docs/translated/` holds English Markdown with YAML frontmatter. This is what gets
  indexed and quoted back to students.
- `docs/data/` holds lookup tables (CSV) queried exactly. Never indexed.

After changing anything under `docs/translated/`, rebuild:

```bash
uv run ioe-index
```

## Development

```bash
uv run ruff check src/ioe/        # lint
uv run ruff format src/ioe/       # format
cd web && npm run lint            # frontend lint
```

Generated artifacts are gitignored and rebuilt with the commands above: `.venv/`,
`.chroma/`, `.cache/`, `web/node_modules/`, `web/.next/`.
