"""Route a query to data, paper, both, or no retrieval source."""

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from agents.llm import get_groq_chat_model


@tool
def choose_query_route(source: Literal["data", "paper", "both", "none"]) -> str:
    """Return the single retrieval route selected for the user's query."""
    return source


ROUTER_PROMPT = """Route each user question to exactly one option:
- data: answers that require measurements, values, spatial or temporal queries,
  statistics, or descriptions of the master ocean dataset.
- paper: answers that require research-paper content, methods, findings, or
  evidence from the indexed paper collection.
- both: answers that need ocean-dataset results and research-paper evidence.
- none: general conversation or questions answerable without either source.

Make sure to have research-paper evidences whenever the query is related to Ocean temperature or ENSO.
Choose data for dataset-specific facts even if the question uses general wording.
Choose paper for questions answerable only from research papers. Do not choose
both unless both sources materially contribute to the requested answer. Return
only one allowed source value and do not include a rationale."""


def route_query(query: str) -> Literal["data", "paper", "both", "none"]:
    """Return only the route label selected by the Groq routing model."""
    if not query.strip():
        raise ValueError("Enter a question to route.")

    router = get_groq_chat_model().bind_tools(
        [choose_query_route],
        tool_choice="required",
    )
    response = router.invoke([
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=query.strip()),
    ])
    for call in response.tool_calls:
        if call["name"] == choose_query_route.name:
            decision = call["args"]
            source = decision.get("source")
            if source not in {"data", "paper", "both", "none"}:
                break
            return source
    raise RuntimeError("The routing model did not return a valid route: data, paper, both, or none.")
