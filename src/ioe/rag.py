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

emb_model = OllamaEmbeddings(model=EMB_MODEL, base_url=OLLAMA_URL)

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
INDEX_DIR = Path(__file__).resolve().parents[2] / ".chroma"
COLLECTION = "ioe_docs"
SKIP_DIRS = {"downloads", "data"}

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
        # downloads/ holds the untranslated source PDFs; data/ holds lookup tables.
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
    """Rebuild the vector store from scratch. Returns the number of chunks indexed."""
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
    return len(chunks)


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
