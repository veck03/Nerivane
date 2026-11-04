"""Search OpenAlex and normalize paper metadata and PDF candidates."""
import os
from typing import Any

import requests

OPENALEX_API = "https://api.openalex.org/works"

def _abstract_from_inverted_index(index: dict[str, list[int]] | None) -> str:
    """Rebuild OpenAlex's position-indexed abstract, when one is available."""
    if not index:
        return ""
    words: list[str] = []
    for word, positions in index.items():
        for position in positions:
            while len(words) <= position:
                words.append("")
            words[position] = word
    return " ".join(word for word in words if word)

def _pdf_urls(work: dict[str, Any]) -> list[str]:
    """Return unique PDF URLs, prioritizing OpenAlex cached content."""

    urls: list[str] = []

    # 1. OpenAlex cached PDF
    content_urls = work.get("content_urls") or {}
    cached_pdf = content_urls.get("pdf")

    if cached_pdf:
        urls.append(cached_pdf)

    # 2. Best Open Access location
    best = work.get("best_oa_location") or {}

    # 3. All other locations
    locations = work.get("locations") or []

    for location in [best, *locations]:
        url = location.get("pdf_url")

        if url and url not in urls:
            urls.append(url)

    return urls


def search_papers(query: str, limit: int, mail_to: str | None = None) -> list[dict[str, Any]]:
    """Find works in OpenAlex and return normalized metadata for each result."""
    params = {
        "search": query,
        "filter": "has_fulltext:true,is_oa:true",
        "per_page": limit,
    }
    if mail_to:
        params["mailto"] = mail_to
    api_key = os.getenv("OPENALEX_API_KEY", "").strip()
    if api_key:
        params["api_key"] = api_key
    response = requests.get(OPENALEX_API, params=params, timeout=30)
    response.raise_for_status()
    results = response.json().get("results", [])
    papers = []
    for work in results:

        work_id = work.get("id")
        if not work_id:
            continue
        authors = [
            author.get("author", {}).get("display_name", "")
            for author in work.get("authorships", [])
        ]
        papers.append({
            "paper_id": work_id,
            "title": work.get("title") or "Untitled",
            "authors": [name for name in authors if name],
            "publication_year": work.get("publication_year"),
            "doi": work.get("doi"),
            "abstract": _abstract_from_inverted_index(work.get("abstract_inverted_index")),
            "pdf_urls": _pdf_urls(work),
        })
    return papers

if __name__ == "__main__":
    QUERY = "urban heat island"
    LIMIT = 5
    papers = search_papers(QUERY, LIMIT)
    for paper in papers:
        {print(paper["title"]),
        print(paper['pdf_urls'])}
