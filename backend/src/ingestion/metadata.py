"""Prepare scalar ChromaDB metadata for each text chunk."""

def chunk_metadata(paper: dict, page_number: int, chunk_index: int, pdf_path: str) -> dict:
    """Combine paper metadata with page and chunk details using scalar values."""
    return {
        "paper_id": paper["paper_id"],
        "title": paper["title"],
        "authors": ", ".join(paper.get("authors", [])),
        "publication_year": paper.get("publication_year") or 0,
        "doi": paper.get("doi") or "",
        "page_number": page_number,
        "chunk_index": chunk_index,
        "pdf_path": pdf_path,
    }
