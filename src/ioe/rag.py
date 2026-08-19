"""Document loading, indexing, and retrieval over the `docs/` folder."""

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
emb_model = OllamaEmbeddings(model=EMB_MODEL)

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"
INDEX_DIR = Path(__file__).resolve().parents[2] / ".chroma"
COLLECTION = "ioe_docs"

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
    for path in sorted(DOCS_DIR.glob("*.md")):
        if path.name.startswith("_") or path.name == "README.md":
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
