"""Start the Ocean Research FastAPI server."""

from pathlib import Path
import sys

import uvicorn
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR / "src"))
load_dotenv(BACKEND_DIR / ".env", override=True)

from src.api.main import app


if __name__ == "__main__":
    uvicorn.run("run_api:app", host="127.0.0.1", port=8000, reload=False)
