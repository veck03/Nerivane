"""Project paths and environment-backed model configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")
DATA_DIR = BACKEND_DIR / "data"
RAW_PDF_DIR = DATA_DIR / "raw_pdfs"
CHROMA_DIR = DATA_DIR / "chroma_db"
PROCESSED_PAPERS_PATH = DATA_DIR / "processed_papers.json"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RERANKER_MODEL = os.getenv(
    "RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L6-v2"
)
RERANKER_CANDIDATE_LIMIT = max(1, int(os.getenv("RERANKER_CANDIDATE_LIMIT", "20")))
RERANKER_ENABLED = os.getenv("RERANKER_ENABLED", "true").strip().lower() in {
    "1", "true", "yes", "on"
}
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_PUBLISHABLE_KEY = (
    os.getenv("SUPABASE_PUBLISHABLE_KEY")
    or os.getenv("SUPABASE_ANON_KEY", "")
)
