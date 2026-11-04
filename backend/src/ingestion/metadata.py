"""Prepare scalar ChromaDB metadata for each text chunk."""

import json

def chunk_metadata(paper: dict, page_number: int, chunk_index: int, pdf_path: str) -> dict:
    """Combine paper metadata with page and chunk details using scalar values."""
    return {
        "paper_id": paper["paper_id"],
        "title": paper["title"],
        "authors": ", ".join(paper.get("authors", [])),
        "authors_json": json.dumps(paper.get("authors", []), ensure_ascii=False),
        "publication_year": paper.get("publication_year") or 0,
        "doi": paper.get("doi") or "",
        "venue": paper.get("venue") or "",
        "paper_url": paper.get("paper_url") or paper["paper_id"],
        "page_number": page_number,
        "chunk_index": chunk_index,
        "pdf_path": pdf_path,
    }
