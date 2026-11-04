"""FastAPI routes for chatting with the Ocean Research agent."""

import logging
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents import answer_query

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Ocean Research API",
    description="Ask questions across the ocean dataset and indexed research papers.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    paper_limit: int = Field(default=5, ge=1, le=20)


class ChatResponse(BaseModel):
    route: Literal["data", "paper", "both", "none"]
    raw_data_output: Any | None = None
    paper_chunks: list[dict[str, Any]] = Field(default_factory=list)
    source_errors: dict[str, str] = Field(default_factory=dict)
    answer: str


@app.get("/api/health")
def health() -> dict[str, str]:
    """Return a lightweight process health response."""
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Send a query through the router and its selected source agents."""
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Query cannot be blank.")

    try:
        result = answer_query(query, paper_limit=request.paper_limit)
    except Exception as error:
        logger.exception("Ocean Research query failed")
        raise HTTPException(
            status_code=500,
            detail="The assistant could not complete this request. Check the backend logs.",
        ) from error

    return ChatResponse(**result)
