"""Coordinate discovery, download, extraction, chunking, and storage."""

from config import CHROMA_DIR, PROCESSED_PAPERS_PATH, RAW_PDF_DIR, EMBEDDING_MODEL
from database.chroma import get_collection
from database.repositories import is_ingested, load_status, save_status, store_chunks, verify_chunks
from ingestion.chunking import split_pages
from ingestion.discovery import search_papers
from ingestion.downloader import download_pdf, paper_pdf_path
from ingestion.embeddings import create_embeddings
from ingestion.metadata import chunk_metadata
from ingestion.processing import extract_pages

def run_pipeline(query: str, limit: int, mail_to: str | None = None) -> dict[str, int]:
    """Run the basic paper ingestion workflow and return count summary."""
    papers = search_papers(query, limit, mail_to)
    collection = get_collection(CHROMA_DIR)
    status = load_status(PROCESSED_PAPERS_PATH)
    summary = {"discovered": len(papers), "skipped": 0, "no_pdf": 0, "downloaded": 0, "ingested": 0, "failed": 0, "chunks": 0}

    for paper in papers:
        paper_id = paper["paper_id"]
        if status.get(paper_id, {}).get("status") == "success" or is_ingested(collection, paper_id):
            summary["skipped"] += 1
            status[paper_id] = {"status": "success", "title": paper["title"]}
            continue

        try:
            expected_pdf = paper_pdf_path(paper_id, RAW_PDF_DIR)
            already_downloaded = expected_pdf.exists() and expected_pdf.stat().st_size > 0
            pdf_path, download_error = download_pdf(paper, RAW_PDF_DIR, mail_to)
            if pdf_path is None:
                summary["no_pdf"] += 1
                status[paper_id] = {"status": "failed", "title": paper["title"], "error": download_error}
                save_status(PROCESSED_PAPERS_PATH, status)
                continue
            if not pdf_path.exists() or pdf_path.stat().st_size == 0:
                raise RuntimeError(download_error or "Downloaded PDF is missing or empty")
            # A previous failed attempt may already have left a usable local PDF.
            if not already_downloaded:
                summary["downloaded"] += 1
            pages = extract_pages(pdf_path)
            if not pages:
                raise RuntimeError("PDF contained no extractable text")
            chunks = split_pages(pages)
            if not chunks:
                raise RuntimeError("PDF produced no text chunks")
            texts = [chunk["text"] for chunk in chunks]
            vectors = create_embeddings(texts, EMBEDDING_MODEL)
            ids = [f"{paper_id}::chunk::{index}" for index in range(len(chunks))]
            metadatas = [chunk_metadata(paper, chunk["page_number"], index, str(pdf_path)) for index, chunk in enumerate(chunks)]
            store_chunks(collection, ids, texts, vectors, metadatas)
            if not verify_chunks(collection, paper_id, len(chunks)):
                raise RuntimeError("ChromaDB verification failed after upsert")
            status[paper_id] = {"status": "success", "title": paper["title"], "chunk_count": len(chunks)}
            save_status(PROCESSED_PAPERS_PATH, status)
            summary["ingested"] += 1
            summary["chunks"] += len(chunks)
        except Exception as error:
            summary["failed"] += 1
            status[paper_id] = {"status": "failed", "title": paper["title"], "error": str(error)}
            save_status(PROCESSED_PAPERS_PATH, status)
            print(f"Failed {paper_id} ({paper['title']}): {error}")

    print("\nIngestion summary")
    print(f"Papers discovered: {summary['discovered']}")
    print(f"Skipped as already processed: {summary['skipped']}")
    print(f"Papers without accessible PDFs: {summary['no_pdf']}")
    print(f"PDFs downloaded or reused: {summary['downloaded']}")
    print(f"Papers successfully ingested: {summary['ingested']}")
    print(f"Papers that failed: {summary['failed']}")
    print(f"Total chunks inserted: {summary['chunks']}")
    return summary
