"""Synthesize the selected source material into a user-facing answer."""

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agents.citation_engine import (
    build_paper_sources,
    validate_answer_citations,
    verify_claim_support,
)
from agents.llm import get_groq_chat_model

FINAL_ANSWER_PROMPT = """You are the final answer agent for an ocean research assistant.
The route field tells you which sources were selected: data, paper, both, or none.
For data, paper, or both, ground source-specific claims only in the supplied
data-tool outputs and paper excerpts. Never invent values, units, dates, paper
claims, or citations. Treat data-tool outputs as source records, but never repeat
their raw JSON, internal tool calls, or stack traces. Summarize only the relevant
results in clear prose or a compact table. For numeric data, report the period,
variable, units, aggregation scope, and NaN handling when available. Cite
paper-supported claims using only
the exact source labels provided, such as [S1] or [S1, p. 4]. Use page numbers
only from the source's available_pages. Do not write a bibliography; the app
builds it from source metadata. If a requested source returned no data or an
error, say so. If route is paper or both and paper_sources is empty, explicitly
say that no indexed paper evidence was retrieved; do not answer paper-specific
claims from general knowledge. If the route is none, answer from general
knowledge or conversational context without claiming dataset or paper evidence.
If the question asks for both sources, connect them only where supplied evidence
supports a connection. Never provide Python, JavaScript, or other plotting code,
and never instruct the user to make the chart manually. Dataset charts are rendered
by the application from structured chart data returned by the tools. When chart_data is
present, briefly describe the plotted values in prose and do not claim that a chart
cannot be generated. If only some requested months have results, clearly identify
the missing months while describing the available chart. Do not suggest switching
to an external dataset; this application is restricted to its connected master
dataset."""


def synthesize_answer(
    query: str,
    route: str,
    raw_data_output: dict | None,
    paper_chunks: list[dict],
    source_errors: dict[str, str],
    verify_citations: bool = False,
) -> dict[str, Any]:
    """Synthesize an answer and validate its paper markers against known sources."""
    paper_sources = build_paper_sources(paper_chunks)
    prompt_sources = [
        {
            "source_id": source["source_id"],
            "title": source["title"],
            "authors": source["authors"],
            "publication_year": source["publication_year"],
            "venue": source["venue"],
            "doi": source["doi"],
            "paper_url": source["paper_url"],
            "available_pages": source["pages"],
            "excerpts": source["excerpts"],
        }
        for source in paper_sources
    ]
    context = {
        "route": route,
        "raw_data_output": raw_data_output,
        "paper_sources": prompt_sources,
        "source_errors": source_errors,
    }
    response = get_groq_chat_model().invoke([
        SystemMessage(content=FINAL_ANSWER_PROMPT),
        HumanMessage(content=(
            f"User query:\n{query}\n\n"
            "Retrieved context (JSON):\n"
            f"{json.dumps(context, indent=2, ensure_ascii=False, default=str)}"
        )),
    ])
    answer = response.content
    if not isinstance(answer, str):
        answer = "\n".join(
            block.get("text", "")
            for block in answer
            if isinstance(block, dict) and block.get("type") == "text"
        ).strip()
    answer, paper_sources, citation_warnings = validate_answer_citations(
        answer, paper_sources, route
    )
    claim_checks = []
    claim_check_status = "not_requested"
    if verify_citations and route not in {"paper", "both"}:
        claim_check_status = "not_applicable"
    if verify_citations and route in {"paper", "both"}:
        try:
            claim_checks, support_warnings = verify_claim_support(
                answer, paper_sources, raw_data_output=raw_data_output
            )
            citation_warnings.extend(support_warnings)
            claim_check_status = (
                "skipped" if not paper_sources and raw_data_output is None else "completed"
            )
        except Exception:
            citation_warnings.append(
                "Optional claim-support check failed; review the paper excerpts manually."
            )
            claim_check_status = "failed"
    return {
        "answer": answer,
        "paper_sources": paper_sources,
        "citation_warnings": list(dict.fromkeys(citation_warnings)),
        "claim_checks": claim_checks,
        "claim_check_status": claim_check_status,
    }
