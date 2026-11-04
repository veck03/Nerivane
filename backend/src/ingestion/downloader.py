"""Download OpenAlex-provided PDF copies to stable local paths."""

from pathlib import Path
from urllib.parse import urlparse

import requests

def paper_pdf_path(paper_id: str, output_dir: Path) -> Path:
    """Build a stable PDF filename from the OpenAlex Work ID."""
    work_id = paper_id.rstrip("/").split("/")[-1]
    return output_dir / f"{work_id}.pdf"

def download_pdf(paper: dict, output_dir: Path, mail_to) -> tuple[Path | None, str | None]:
    """Try provided OpenAlex PDF URLs in order; return path or a skip reason."""
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = paper_pdf_path(paper["paper_id"], output_dir)
    if destination.exists() and destination.stat().st_size:
        return destination, None
    urls = paper.get("pdf_urls", [])
    if not urls:
        return None, "OpenAlex did not provide a PDF URL"
    errors = []
    for url in urls:
        try:
            response = requests.get(url, timeout=60, headers={"User-Agent": "OceanRAG/1.0 (research ingestion)"}) #may change useragent later
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if "pdf" not in content_type and not response.content.startswith(b"%PDF"):
                errors.append(f"{urlparse(url).netloc} did not return a PDF")
                continue
            if not response.content.startswith(b"%PDF"):
                errors.append(f"{urlparse(url).netloc} returned an invalid PDF")
                continue
            temporary = destination.with_suffix(".pdf.tmp")
            temporary.write_bytes(response.content)
            temporary.replace(destination)
            return destination, None
        except requests.RequestException as error:
            errors.append(f"{urlparse(url).netloc}: {error}")
    return None, "Could not download an OpenAlex PDF URL: " + "; ".join(errors)
