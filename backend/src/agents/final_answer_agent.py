"""Synthesize the selected source material into a user-facing answer."""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import get_groq_chat_model

FINAL_ANSWER_PROMPT = """You are the final answer agent for an ocean research assistant.
The route field tells you which sources were selected: data, paper, both, or none.
For data, paper, or both, ground source-specific claims only in the supplied
data-tool outputs and paper chunks. Never invent values, units, dates, paper
claims, or citations. Treat data-tool outputs as raw source records and explain
them clearly. For numeric data, report the period, variable, units, aggregation
scope, and NaN handling when available. For paper evidence, cite the supplied
paper title and page number when present. If a requested source returned no data
or an error, say so. If the route is none, answer from general knowledge or
conversational context without claiming dataset or paper evidence. If the
question asks for both sources, connect them only where supplied evidence
supports a connection."""


def synthesize_answer(
    query: str,
    route: str,
    raw_data_output: dict | None,
    paper_chunks: list[dict],
    source_errors: dict[str, str],
) -> str:
    """Give the final agent the selected route and only gathered context."""
    context = {
        "route": route,
        "raw_data_output": raw_data_output,
        "paper_chunks": paper_chunks,
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
    return answer
