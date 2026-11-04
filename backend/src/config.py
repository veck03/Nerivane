"""Project paths and environment-backed model configuration."""

from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
RAW_PDF_DIR = DATA_DIR / "raw_pdfs"
CHROMA_DIR = DATA_DIR / "chroma_db"
PROCESSED_PAPERS_PATH = DATA_DIR / "processed_papers.json"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

load_dotenv(BACKEND_DIR / ".env")
