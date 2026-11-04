"""Coordinate routing, selected retrieval agents, and final answer synthesis."""

from agents.final_answer_agent import synthesize_answer
from agents.ocean_data_agent import run_ocean_data_agent
from agents.router_agent import route_query
from retrieval import retrieve_paper_chunks


def answer_query(query: str, paper_limit: int = 5) -> dict:
    """Route a query, run only its selected source agents, and synthesize."""
    if not query.strip():
        raise ValueError("Enter a question.")

    route = route_query(query)
    raw_data_output = None
    paper_chunks = []
    source_errors: dict[str, str] = {}

    if route in {"data", "both"}:
        try:
            raw_data_output = run_ocean_data_agent(query)
        except Exception as error:
            source_errors["data"] = str(error)

    if route in {"paper", "both"}:
        try:
            # This call lazily loads the local Hugging Face embedding model.
            paper_chunks = retrieve_paper_chunks(query, limit=paper_limit)
        except Exception as error:
            source_errors["paper"] = str(error)

    answer = synthesize_answer(
        query=query,
        route=route,
        raw_data_output=raw_data_output,
        paper_chunks=paper_chunks,
        source_errors=source_errors,
    )
    return {
        "route": route,
        "raw_data_output": raw_data_output,
        "paper_chunks": paper_chunks,
        "source_errors": source_errors,
        "answer": answer,
    }
