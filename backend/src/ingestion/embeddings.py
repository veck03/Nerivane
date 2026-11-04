"""Generate local sentence-transformer embeddings through LangChain."""

from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings


@lru_cache(maxsize=2)
def _get_embedding_model(model: str) -> HuggingFaceEmbeddings:
    """Load a local model once and reuse it across papers and query lookups."""
    return HuggingFaceEmbeddings(model_name=model)


def create_embeddings(texts: list[str], model: str) -> list[list[float]]:
    """Embed chunk strings locally and return vectors in matching order."""
    return _get_embedding_model(model).embed_documents(texts)
