"""A small tool-calling agent for questions about the master ocean dataset."""

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from agents.llm import get_groq_chat_model
from tools import OCEAN_DATA_TOOLS

SYSTEM_PROMPT = """You are the Ocean Data tool agent. Select and call the tools needed to
retrieve raw results from ocean_q1_2020.zarr. Do not write a polished answer or
summarize results in prose; the final answer agent will do that. Use only the
connected dataset tools. For surface temperature use sst; for subsurface
temperature use thetao and specify a depth. If a request cannot be served by a
tool, return no more tool calls. Do not treat predicted_temperature as a forecast
unless the question asks for it; its lead time is unknown."""

MAX_TOOL_ROUNDS = 3


def run_ocean_data_agent(question: str) -> dict:
    """Run the data tools selected by the LLM and return their raw outputs.

    Args:
        question: A natural-language question requiring ocean dataset values.

    Returns:
        Tool names and unedited tool results for the final answer agent.
    """
    if not question.strip():
        raise ValueError("Enter a question about the ocean dataset.")

    model_with_tools = get_groq_chat_model().bind_tools(OCEAN_DATA_TOOLS)
    available_tools = {data_tool.name: data_tool for data_tool in OCEAN_DATA_TOOLS}
    raw_outputs = []
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=question.strip()),
    ]

    tool_rounds = 0
    while True:
        response = model_with_tools.invoke(messages)
        if not response.tool_calls:
            return {
                "question": question,
                "tool_outputs": raw_outputs,
                "status": "complete" if raw_outputs else "no_data_tool_called",
            }

        if tool_rounds >= MAX_TOOL_ROUNDS:
            return {
                "question": question,
                "tool_outputs": raw_outputs,
                "status": "tool_round_limit_reached",
            }

        messages.append(response)
        for tool_call in response.tool_calls:
            selected_tool = available_tools.get(tool_call["name"])
            if selected_tool is None:
                tool_result = f"Unknown data tool: {tool_call['name']}"
            else:
                try:
                    tool_result = selected_tool.invoke(tool_call["args"])
                except Exception as error:
                    tool_result = f"Data lookup error: {error}"
            raw_outputs.append({
                "tool": tool_call["name"],
                "arguments": tool_call["args"],
                "output": tool_result,
            })
            messages.append(
                ToolMessage(
                    content=str(tool_result),
                    tool_call_id=tool_call["id"],
                    name=tool_call["name"],
                )
            )
        tool_rounds += 1
