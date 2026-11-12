"""Rerank hybrid-retrieval candidates with a local cross-encoder."""

from collections import defaultdict
from functools import lru_cache
from typing import Any

from sentence_transformers import CrossEncoder

from config import RERANKER_MODEL


@lru_cache(maxsize=1)
def _get_reranker() -> CrossEncoder:
    """Load the cross-encoder once and reuse it for later paper queries."""
    return CrossEncoder(RERANKER_MODEL)


def rerank_paper_chunks(
    query: str,
    candidates: list[dict[str, Any]],
    limit: int,
    max_chunks_per_paper: int = 2,
) -> list[dict[str, Any]]:
    """Sort candidates by query/chunk relevance and return a diverse top list.

    Cross-encoder scores are ranking scores, not calibrated probabilities.
    Original hybrid scores and match metadata are retained for inspection.
    """
    if not candidates or limit < 1:
        return []

    pairs = [(query, candidate.get("text") or "") for candidate in candidates]
    scores = _get_reranker().predict(pairs, show_progress_bar=False)
    ranked = []
    for candidate, score in zip(candidates, scores, strict=True):
        result = dict(candidate)
        result["rerank_score"] = round(float(score), 6)
        ranked.append(result)
    ranked.sort(key=lambda item: item["rerank_score"], reverse=True)

    selected = []
    deferred = []
    paper_counts: dict[str, int] = defaultdict(int)
    for item in ranked:
        metadata = item.get("metadata") or {}
        paper_id = str(metadata.get("paper_id") or item.get("chunk_id") or "unknown")
        if paper_counts[paper_id] < max_chunks_per_paper:
            selected.append(item)
            paper_counts[paper_id] += 1
        else:
            deferred.append(item)
        if len(selected) >= limit:
            break

    if len(selected) < limit:
        selected.extend(deferred[:limit - len(selected)])

    for rank, item in enumerate(selected, start=1):
        item["rerank_rank"] = rank
    return selected
