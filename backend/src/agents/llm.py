"""Shared Groq chat-model configuration for the routing and answer agents."""

import os

from langchain_openai import ChatOpenAI

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"


def get_groq_chat_model() -> ChatOpenAI:
    """Create the configured Groq chat model using GROQ_API_KEY from env."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to backend/.env and restart the app.")
    return ChatOpenAI(
        model=os.getenv("GROQ_CHAT_MODEL", DEFAULT_GROQ_MODEL),
        api_key=api_key,
        base_url=GROQ_BASE_URL,
        temperature=0,
    )
