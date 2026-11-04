"""Create or open the persistent ChromaDB research collection."""

from pathlib import Path

import chromadb

def get_collection(database_dir: Path):
    """Return the persistent research_papers collection."""
    database_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(database_dir))
    return client.get_or_create_collection(name="research_papers")
