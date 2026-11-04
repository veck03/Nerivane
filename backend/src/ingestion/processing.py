"""Extract page text from PDFs with PyMuPDF."""

from pathlib import Path

import fitz

def extract_pages(pdf_path: Path) -> list[dict[str, int | str]]:
    """Read a PDF and return nonempty page text with one-based page numbers."""
    pages = []
    with fitz.open(pdf_path) as document:
        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append({"page_number": page_number, "text": text})
    return pages
