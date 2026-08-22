"""The conversation index behind the history sidebar.

The checkpointer already stores every message, but it stores them keyed by thread id and
nothing else -- it cannot answer "which conversations does this browser have, and what
was each one about". This module keeps that one small table alongside the checkpoints,
in the same SQLite file, so a conversation and its label are never separated.

Conversations are scoped to the browser that started them. There are no accounts here,
so the scope is a random id the browser keeps: it is not a security boundary -- anyone
with the file can read the table -- but it stops one student's list of questions from
appearing in another's sidebar, and those questions ("Did form 2083-4001 pass?") name
real people.

Titles are written by the model from the opening question, because the opening question
is usually too long to sit in a 14rem column: "How do I pay the entrance exam fee with
eSewa if I already submitted the form?" has to become "Paying the fee with eSewa". A
truncated question would fit too, but it would cut mid-word at the point the sentence
was about to become specific.
"""

import asyncio
import datetime
import re
import sqlite3
from pathlib import Path

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

from ioe.rag import OLLAMA_URL

# Beside the notice cache, on the same volume: a conversation a student can come back to
# has to outlive the container that answered it.
DB_PATH = Path(__file__).resolve().parents[2] / ".cache" / "conversations.sqlite3"

TITLE_MODEL = "qwen2.5:7b"
# Long enough to name a topic, short enough that the column never has to ellipsize a
# title that had something left to say.
MAX_TITLE_CHARS = 48

TITLE_PROMPT = """Write a title for a conversation that opens with this question from a \
student asking about IOE entrance exams and admission.

Rules:
- At most six words.
- Name the topic, not the person: "Quota application documents", not "Student asks about \
quota".
- Sentence case, so a column of these reads as a list rather than as headlines.
- No quotation marks, no trailing full stop, no preamble.
- If the question is not about IOE admissions, title it by whatever it is actually about.

Question: {question}

Title:"""

# Small budget: a title is a handful of tokens, and capping the generation is what keeps
# this from becoming a second answer the student is waiting on.
title_model = ChatOllama(
    model=TITLE_MODEL, base_url=OLLAMA_URL, num_predict=24, temperature=0.2
)


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # The checkpointer holds its own connection to this same file, so both have to agree
    # on WAL or one of them will sit behind the other's write lock.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS threads (
            thread_id  TEXT PRIMARY KEY,
            client_id  TEXT NOT NULL DEFAULT '',
            title      TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            turns      INTEGER NOT NULL DEFAULT 0
        )"""
    )
    # Carries a database written before the column existed, rather than failing on it.
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(threads)")}
    if "client_id" not in columns:
        conn.execute(
            "ALTER TABLE threads ADD COLUMN client_id TEXT NOT NULL DEFAULT ''"
        )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS threads_recent ON threads(client_id, updated_at DESC)"
    )
    return conn


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")


def fallback_title(question: str) -> str:
    """The question itself, tidied -- used before the model answers and if it fails.

    A conversation is never nameless: an untitled row in the sidebar is indistinguishable
    from a broken one.
    """
    text = " ".join(question.split()) or "New conversation"
    if len(text) <= MAX_TITLE_CHARS:
        return text
    # Cut on a word boundary so the label reads as an abbreviation rather than damage.
    return text[:MAX_TITLE_CHARS].rsplit(" ", 1)[0] + "…"


# Names this domain writes a particular way. The model gets them right most of the time
# and mangles them the rest ("barch entrance syllabus"), and a title is short enough that
# one wrong name is the whole label.
NAMES = {
    "ioe": "IOE",
    "tu": "TU",
    "barch": "BArch",
    "b.arch": "B.Arch",
    "esewa": "eSewa",
    "khalti": "Khalti",
    "pulchowk": "Pulchowk",
    "thapathali": "Thapathali",
    "purwanchal": "Purwanchal",
    "paschimanchal": "Paschimanchal",
    "chitwan": "Chitwan",
    "nepal": "Nepal",
    "ictc": "ICTC",
}


def _sentence_case(text: str) -> str:
    """One casing for the whole column, whatever casing the model felt like using.

    Asking the model for sentence case does not hold -- it answers in Title Case about
    half the time, and the one run where it complied it also lowercased "BArch". So the
    prompt asks and this decides: a word is left as written if it carries a capital of
    its own past the first letter (IOE, BArch, eSewa) or contains a digit, and is
    lowercased otherwise. The first word is capitalised unless it is one of those names,
    since "eSewa payment method" must not become "ESewa payment method".
    """
    words = []
    for i, word in enumerate(text.split(" ")):
        bare = word.strip(",:;")
        known = NAMES.get(bare.lower())
        if known:
            word = word.replace(bare, known)
        elif any(c.isupper() for c in word[1:]) or any(c.isdigit() for c in word):
            pass
        elif i == 0:
            word = word[:1].upper() + word[1:]
        else:
            word = word.lower()
        words.append(word)
    return " ".join(words)


def _clean(raw: str, question: str) -> str:
    """Strip the flourishes a 7B model adds to a title it was told not to decorate."""
    text = " ".join(raw.split())
    text = text.split("\n")[0]
    # Models reliably return **Title:** "Something." despite being asked for none of it.
    text = re.sub(
        r"^(title|conversation title)\s*[:\-]\s*", "", text, flags=re.IGNORECASE
    )
    text = text.strip(" *_#").strip().strip("\"'“”‘’").rstrip(".").strip()
    if not text or len(text) > MAX_TITLE_CHARS:
        return fallback_title(question)
    return _sentence_case(text)


def make_title(question: str) -> str:
    """Name a conversation from its opening question. Never raises."""
    try:
        reply = title_model.invoke(
            [HumanMessage(content=TITLE_PROMPT.format(question=question))]
        )
    except Exception:  # noqa: BLE001 - a title is a convenience; the conversation is not
        return fallback_title(question)
    return _clean(reply.content or "", question)


# --- the table -------------------------------------------------------------------------


def _record(thread_id: str, client_id: str, title: str) -> None:
    with _connect() as conn:
        conn.execute(
            """INSERT INTO threads
                   (thread_id, client_id, title, created_at, updated_at, turns)
               VALUES (?, ?, ?, ?, ?, 1)
               ON CONFLICT(thread_id) DO UPDATE SET
                   updated_at = excluded.updated_at,
                   turns      = threads.turns + 1""",
            (thread_id, client_id, title, _now(), _now()),
        )


def _retitle(thread_id: str, title: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE threads SET title = ? WHERE thread_id = ?", (title, thread_id)
        )


def _listing(client_id: str, limit: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """SELECT thread_id, title, created_at, updated_at, turns FROM threads
               WHERE client_id = ? ORDER BY updated_at DESC LIMIT ?""",
            (client_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def _forget(thread_id: str) -> bool:
    with _connect() as conn:
        return (
            conn.execute(
                "DELETE FROM threads WHERE thread_id = ?", (thread_id,)
            ).rowcount
            > 0
        )


def _exists(thread_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM threads WHERE thread_id = ?", (thread_id,)
        ).fetchone()
    return row is not None


# SQLite is fast here but still blocking, and the event loop is also streaming tokens.
async def record(thread_id: str, client_id: str, title: str) -> None:
    await asyncio.to_thread(_record, thread_id, client_id, title)


async def retitle(thread_id: str, title: str) -> None:
    await asyncio.to_thread(_retitle, thread_id, title)


async def listing(client_id: str, limit: int = 60) -> list[dict]:
    return await asyncio.to_thread(_listing, client_id, limit)


async def forget(thread_id: str) -> bool:
    return await asyncio.to_thread(_forget, thread_id)


async def exists(thread_id: str) -> bool:
    return await asyncio.to_thread(_exists, thread_id)
