"""Command-line entry point for research paper ingestion."""

import os
import sys
from dotenv import load_dotenv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from src.ingestion.pipeline import run_pipeline

load_dotenv(Path(__file__).resolve().parent / ".env")

QUERY = "ocean temperature profile"
LIMIT = 25
MAILTO = os.getenv("MAIL_TO", "").strip() or None

def main():
    run_pipeline(QUERY, LIMIT, MAILTO)


if __name__ == "__main__":
    main()
