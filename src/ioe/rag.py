"""Document loading, indexing, and retrieval over the `docs/` folder."""

import os
import re
from pathlib import Path

import yaml
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

EMB_MODEL = "bge-m3:latest"

# A container's own localhost is not the host's, so where Ollama lives is configurable.
OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"

# Every ChatOllama in this process must be constructed with this value.
#
# Left unset, Ollama serves qwen2.5:7b at 4096 tokens -- measured on the running server,
# /api/ps reporting "context_length": 4096 -- and a real fee question assembles about
# 5,300 tokens of prompt before the conversation is added to it: 2,131 for the system
# prompt, 1,656 for six retrieved chunks, 1,161 for the worked fee figures, the rest for
# the notice feed and the date blocks. What does not fit is dropped, silently and without
# an error, and the system prompt is dropped first because it is at the front.
#
# Measured directly: an 8,040-token prompt sent at 4096 evaluated only 2,050 tokens, and
# the model answered from the filler at the end rather than from the instruction at the
# start, which it never saw. The same prompt at 8192 evaluated 8,037 and answered
# correctly. Every prompt rule this app has added over twenty-three issues has been
# competing for a window half the size it needed.
#
# 16384 measured at 5.47 GB of VRAM against the 8.19 GB card this runs on, against 4.99 GB
# at 8192 -- the headroom is worth more than the half gigabyte. num_ctx is a load-time
# option, so two ChatOllama instances that disagree about it make Ollama hold two runners,
# and two runners do not fit. Hence: one constant, here, next to the URL they all share.
NUM_CTX = 16384

emb_model = OllamaEmbeddings(model=EMB_MODEL, base_url=OLLAMA_URL)

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
INDEX_DIR = Path(__file__).resolve().parents[2] / ".chroma"
COLLECTION = "ioe_docs"
SKIP_DIRS = {"downloads", "data", "engineering"}

# Sections longer than this are split again; overlap keeps a split table or list readable.
MAX_CHUNK = 1200
CHUNK_OVERLAP = 150


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (metadata, body). Documents without frontmatter yield an empty dict."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = yaml.safe_load(parts[1]) or {}
    return (meta if isinstance(meta, dict) else {}), parts[2].lstrip("\n")


def load_documents() -> list[Document]:
    """Chunk every indexable file in docs/ on its Markdown headings."""
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
        strip_headers=False,
    )
    size_splitter = RecursiveCharacterTextSplitter(
        chunk_size=MAX_CHUNK, chunk_overlap=CHUNK_OVERLAP
    )

    chunks: list[Document] = []
    for path in sorted(DOCS_DIR.rglob("*.md")):
        if path.name.startswith("_") or path.name == "README.md":
            continue
        # downloads/ holds the untranslated source PDFs; data/ holds lookup tables;
        # engineering/ is documentation about this software, not about admissions.
        if any(part in SKIP_DIRS for part in path.relative_to(DOCS_DIR).parts[:-1]):
            continue

        meta, body = _split_frontmatter(path.read_text(encoding="utf-8"))
        if not body.strip():
            continue

        # Chroma rejects None and non-scalar metadata, so keep only populated scalars.
        base = {k: v for k, v in meta.items() if isinstance(v, (str, int, float, bool))}
        base["file"] = path.name

        for section in size_splitter.split_documents(header_splitter.split_text(body)):
            section.metadata = {**section.metadata, **base}
            chunks.append(section)

    return chunks


def build_index() -> int:
    """Rebuild the vector store from scratch. Returns the number of chunks indexed.

    Notice records go back in afterwards. Resetting the collection drops them along with
    everything else, and a rebuild that leaves the assistant blind to the notice feed
    until the next refresh is a rebuild that reintroduces the bug this was written for.
    """
    chunks = load_documents()

    store = Chroma(
        collection_name=COLLECTION,
        embedding_function=emb_model,
        persist_directory=str(INDEX_DIR),
        collection_metadata={"hnsw:space": "cosine"},
    )
    store.reset_collection()
    if chunks:
        store.add_documents(chunks)
    refresh_notice_index(rebuilt=True)
    return len(chunks)


# Notice records live in the same collection as the documents, so one search covers both
# and the citation machinery treats them identically. The id is the notice's URL, which
# makes writing them an upsert and lets a notice that has dropped off the feed be removed
# by id rather than by guesswork.
NOTICE_ID = "notice::"


def notice_documents(payload: dict) -> list[Document]:
    """One short record per cached notice: what was published, by whom, and when.

    The notice pages themselves are not indexed -- see the note in notices.py, they are
    scanned PDFs behind a "Click Here" -- so a record does not claim to know what a notice
    says. It knows that it exists and when, which is the question that was being answered
    wrongly: asked whether anything had been published this week, the assistant used to
    say no while the app displayed a notice from the day before.
    """
    docs: list[Document] = []
    for notice in payload.get("notices", []):
        title = (notice.get("title") or "").strip()
        url = (notice.get("url") or "").strip()
        if not title or not url:
            continue
        source = notice.get("source_label") or "IOE"
        ad = notice.get("date") or ""
        bs = notice.get("bs_date") or ""
        when = f"{bs} BS ({ad} AD)" if bs and ad else (ad or bs or "an unstated date")
        docs.append(
            Document(
                page_content=(
                    f"Notice published by {source}: {title}\n"
                    f"Publication date: {when}.\n"
                    "This is a notice listing from the official feed. The notice itself "
                    "is published as a document at the linked page."
                ),
                metadata={
                    "kind": "notice",
                    "title": title,
                    "url": url,
                    # source_payload groups citations by `file`; a notice is its own URL.
                    "file": url,
                    "year": bs.split("/")[0] if bs else "",
                    "source": source,
                    "date": ad,
                },
            )
        )
    return docs


def index_notices(payload: dict, previous: list[str] | None = None) -> list[str]:
    """Replace the indexed notice records with the ones in `payload`. Returns their ids.

    Ids of notices that have rolled off the feed are deleted, so the index tracks the
    listing rather than growing without bound.
    """
    docs = notice_documents(payload)
    ids = [f"{NOTICE_ID}{doc.metadata['url']}" for doc in docs]
    store = get_store()

    gone = [i for i in (previous or []) if i not in set(ids)]
    if gone:
        # A reset collection has none of these; deleting what is not there is not an error
        # worth failing a refresh over.
        try:
            store.delete(ids=gone)
        except Exception:  # noqa: BLE001 - see above
            gone = []
    if docs:
        store.add_documents(docs, ids=ids)
    return ids


def refresh_notice_index(rebuilt: bool = False) -> int:
    """Bring the indexed notice records in line with the cache. Returns how many.

    The ids written last time are kept in the notice cache beside the notices themselves,
    so this knows what to remove without scanning the collection. After a full rebuild
    there is nothing to remove -- the reset took everything with it.
    """
    from ioe import notices

    payload = notices.load()
    previous = [] if rebuilt else payload.get("indexed_ids") or []
    ids = index_notices(payload, previous)
    notices.remember_indexed(ids)
    return len(ids)


def get_store() -> Chroma:
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=emb_model,
        persist_directory=str(INDEX_DIR),
        collection_metadata={"hnsw:space": "cosine"},
    )


def citation(doc: Document) -> str:
    """A short source label the model can repeat back to the student."""
    meta = doc.metadata
    label = meta.get("title") or meta.get("file", "source")
    year = meta.get("year")
    return f"{label} ({year})" if year else str(label)


# One citation per document, capped at what a student will actually click through.
# Retrieval routinely returns several chunks of the same notice; listing each one would
# make a three-source answer look like a six-source answer.
MAX_SOURCES = 3
MAX_SECTIONS = 2

# How far below the best hit a document may sit and still be named. Questions that
# genuinely span notices keep all of them -- "what documents do I need for a quota"
# cites three, within 0.02 of each other -- while a question one notice answers outright
# cites that one, instead of trailing the four next-nearest things in the index behind it.
CITATION_MARGIN = 0.03

# Being in the prompt and being worth naming are different things, and no relevance score
# can tell them apart: "How do I apply to Kathmandu University?" scores 0.63 against these
# notices, higher than several real IOE questions, and the honest answer to it is a
# refusal. So a document is named only if the answer visibly used it -- if the two share
# distinctive wording that is in neither the question nor the boilerplate.
#
# The fraction is what separates, measured over eighteen real answers: what a grounded
# answer says is mostly what its document says (0.17-0.75 of it), while a refusal is
# mostly about the question (0.02-0.15). The band between those is narrow, so the cut
# sits in it and errs downward -- losing a citation costs a link the student can still
# find in the rail, while inventing one puts a source under a sentence it never wrote.
#
# The count guards the other end. A three-word answer that happens to share one term
# scores a third by fraction alone, and that is noise, not grounding.
MIN_SHARED_TERMS = 4
MIN_SHARED_FRACTION = 0.16

_TERM = re.compile(r"[a-z0-9][a-z0-9./-]{3,}")

# Words that say nothing about which document an answer came from. The domain terms are
# here for the same reason as the English ones: every notice in this corpus is about IOE
# entrance examinations, so matching on "admission" identifies nothing.
_BOILERPLATE = """about above after again against also among and any are because
been before being below between both cannot could does doing down during each few for
from further had has have having here how into itself just more most must not now off
once only other ought our ours out over own same should some such than that the their
theirs them then there these they this those through too under until very was were what
when where which while who whom why will with would you your yours
entrance exam examination admission admissions question questions answer information
notice notices student students apply application applications ioe institute engineering
tribhuvan university campus campuses please help handle can may need"""
# Split off the literal so SIM905 does not rewrite the list into one unreadable line.
_COMMON = frozenset(_BOILERPLATE.split())


def distinctive(text: str) -> set[str]:
    """The words in a passage that could identify it. Lowercased, no boilerplate."""
    return {word for word in _TERM.findall(text.lower()) if word not in _COMMON}


def source_payload(scored: list[tuple[Document, float]]) -> list[dict]:
    """Candidate citations: one per document, best first, near-misses dropped.

    These are what retrieval put in the prompt, not markers the model was asked to emit.
    A 7B model does not reliably produce those, and a citation that is sometimes there is
    worse than none: the student cannot tell a missing marker from an ungrounded answer.

    Each entry carries the document's distinctive terms so that keep_grounded can check
    the finished answer against it. chat_node strips them before the citation is stored.
    """
    if not scored:
        return []

    # Sorted rather than assumed sorted: rerank passes hits through untouched for
    # questions about foreign applicants.
    ranked = sorted(scored, key=lambda pair: pair[1], reverse=True)
    best = ranked[0][1]

    out: dict[str, dict] = {}
    for doc, score in ranked:
        if best - score > CITATION_MARGIN:
            break
        meta = doc.metadata
        file = str(meta.get("file", "source"))
        entry = out.setdefault(
            file,
            {
                "title": str(meta.get("title") or file),
                "year": str(meta["year"]) if meta.get("year") else None,
                "url": meta.get("url") or None,
                "file": file,
                "sections": [],
                "terms": [],
            },
        )
        # h1 restates the document title in every one of these notices, so a citation
        # pointing at it would add nothing the title has not already said.
        section = meta.get("h3") or meta.get("h2")
        if section and section not in entry["sections"]:
            entry["sections"].append(str(section))
        entry["terms"] = sorted(set(entry["terms"]) | distinctive(doc.page_content))

    for entry in out.values():
        del entry["sections"][MAX_SECTIONS:]
    return list(out.values())[:MAX_SOURCES]


def keep_grounded(answer: str, question: str, sources: list[dict]) -> list[dict]:
    """Drop candidates the answer did not visibly draw on, and shed the term lists.

    Terms the question itself supplied are discounted on both sides: a document does not
    earn a citation by echoing the words it was searched with.
    """
    asked = distinctive(question)
    written = distinctive(answer) - asked
    if not written:
        return []

    kept = []
    for source in sources:
        shared = written & (set(source["terms"]) - asked)
        if (
            len(shared) >= MIN_SHARED_TERMS
            and len(shared) / len(written) >= MIN_SHARED_FRACTION
        ):
            kept.append({key: value for key, value in source.items() if key != "terms"})
    return kept


def format_context(docs: list[Document]) -> str:
    blocks = []
    for doc in docs:
        header = f"[Source: {citation(doc)}]"
        url = doc.metadata.get("url")
        if url:
            header += f"\n[URL: {url}]"
        blocks.append(f"{header}\n{doc.page_content.strip()}")
    return "\n\n---\n\n".join(blocks)


def main() -> None:
    """Entry point for `uv run ioe-index`."""
    count = build_index()
    if count:
        print(f"indexed {count} chunks from {DOCS_DIR}")
    else:
        print(f"no documents found in {DOCS_DIR} - index is empty")


if __name__ == "__main__":
    main()


# Most applicants are Nepali nationals, so documents written only for foreign applicants
# are demoted unless the question actually signals one. The penalty is larger than the
# spread between competing chunks on a quota question (~0.03), so it reliably reorders,
# but small enough that a foreign-only document still surfaces when nothing else matches.
FOREIGN_PENALTY = 0.10
_FOREIGN_HINTS = re.compile(
    r"\b(foreign|foreigner|foreigners|international|non-?nepali|overseas|abroad|"
    r"embassy|passport|nrn|expatriate)\b",
    re.IGNORECASE,
)


def mentions_foreign_applicant(query: str) -> bool:
    return bool(_FOREIGN_HINTS.search(query))


def rerank(
    query: str, hits: list[tuple[Document, float]]
) -> list[tuple[Document, float]]:
    """Re-order hits so the majority audience leads, without dropping anything."""
    if mentions_foreign_applicant(query):
        return hits

    adjusted = [
        (
            doc,
            score - FOREIGN_PENALTY
            if doc.metadata.get("audience") == "foreign"
            else score,
        )
        for doc, score in hits
    ]
    return sorted(adjusted, key=lambda pair: pair[1], reverse=True)
