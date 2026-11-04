"""Simple JSON status tracking and ChromaDB paper operations."""

import json
from pathlib import Path

def load_status(path: Path) -> dict:
    """Load persistent paper status, returning an empty mapping on first run."""
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        raise RuntimeError(f"Could not read ingestion status file: {path}")

def save_status(path: Path, status: dict) -> None:
    """Atomically save the current ingestion status as readable JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(status, indent=2), encoding="utf-8")
    temporary.replace(path)

def is_ingested(collection, paper_id: str) -> bool:
    """Check ChromaDB for at least one chunk belonging to this paper."""
    result = collection.get(where={"paper_id": paper_id}, limit=1, include=[])
    return bool(result.get("ids"))

def store_chunks(collection, ids: list[str], texts: list[str], embeddings: list[list[float]], metadata: list[dict]) -> None:
    """Upsert chunk records so retries cannot create duplicate vector IDs."""
    collection.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadata)

def verify_chunks(collection, paper_id: str, expected_count: int) -> bool:
    """Confirm expected unique IDs exist and every fetched record has this paper ID."""
    result = collection.get(where={"paper_id": paper_id}, include=["metadatas"])
    ids = result.get("ids", [])
    metadatas = result.get("metadatas", [])
    return len(ids) == expected_count and all(item.get("paper_id") == paper_id for item in metadatas)
