"""FastAPI routes for chatting with the Ocean Research agent."""

from contextlib import asynccontextmanager
import logging
from typing import Any, AsyncIterator, Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

from agents import answer_query
from api.auth import AuthenticatedUser, get_authenticated_user
from config import EMBEDDING_MODEL
from ingestion.embeddings import load_embedding_model

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Preload the local embedding model before serving API requests."""
    logger.info("Loading and warming embedding model: %s", EMBEDDING_MODEL)
    load_embedding_model(EMBEDDING_MODEL)
    logger.info("Embedding model is ready.")
    yield


app = FastAPI(
    title="Ocean Research API",
    description="Ask questions across the ocean dataset and indexed research papers.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    paper_limit: int = Field(default=5, ge=1, le=20)
    publication_year_from: int | None = Field(default=None, ge=1800, le=2100)
    publication_year_to: int | None = Field(default=None, ge=1800, le=2100)
    verify_citations: bool = False

    @model_validator(mode="after")
    def validate_publication_year_range(self):
        if (
            self.publication_year_from is not None
            and self.publication_year_to is not None
            and self.publication_year_from > self.publication_year_to
        ):
            raise ValueError("publication_year_from cannot be later than publication_year_to")
        return self


class ChatResponse(BaseModel):
    route: Literal["data", "paper", "both", "none"]
    raw_data_output: Any | None = None
    paper_chunks: list[dict[str, Any]] = Field(default_factory=list)
    paper_sources: list[dict[str, Any]] = Field(default_factory=list)
    citation_warnings: list[str] = Field(default_factory=list)
    claim_checks: list[dict[str, Any]] = Field(default_factory=list)
    claim_check_status: Literal["not_requested", "not_applicable", "completed", "skipped", "failed"] = "not_requested"
    source_errors: dict[str, str] = Field(default_factory=dict)
    answer: str


@app.get("/api/health")
def health() -> dict[str, str]:
    """Return a lightweight process health response."""
    return {"status": "ok"}


@app.get("/api/auth/me")
def auth_me(current_user: AuthenticatedUser = Depends(get_authenticated_user)) -> dict[str, str | None]:
    """Return the verified user's identity and application role."""
    return {
        "id": current_user.user_id,
        "email": current_user.email,
        "app_role": current_user.app_role,
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    _current_user: AuthenticatedUser = Depends(get_authenticated_user),
) -> ChatResponse:
    """Send a query through the router and its selected source agents."""
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Query cannot be blank.")

    try:
        result = answer_query(
            query,
            paper_limit=request.paper_limit,
            publication_year_from=request.publication_year_from,
            publication_year_to=request.publication_year_to,
            verify_citations=request.verify_citations,
        )
    except Exception as error:
        logger.exception("Ocean Research query failed")
        raise HTTPException(
            status_code=500,
            detail="The assistant could not complete this request. Check the backend logs.",
        ) from error

    return ChatResponse(**result)
