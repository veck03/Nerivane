"""Retrieve research-paper chunks with dense and BM25 keyword search."""

import re
from collections import defaultdict

from rank_bm25 import BM25Okapi

from config import CHROMA_DIR, EMBEDDING_MODEL
from database.chroma import get_collection
from ingestion.embeddings import create_embeddings

RRF_CONSTANT = 60


def _tokens(text: str) -> list[str]:
    """Return lowercase word tokens for the BM25 keyword ranker."""
    return re.findall(r"[a-z0-9]+", text.lower())


def retrieve_paper_chunks(
    query: str,
    limit: int = 5,
    publication_year_from: int | None = None,
    publication_year_to: int | None = None,
) -> list[dict]:
    """Return ranked paper chunks by reciprocal-rank-fused dense and BM25 search.

    Dense search embeds the query with the same local model used during
    ingestion. Keyword search ranks stored chunk text with BM25. The two ranked
    lists are merged with reciprocal rank fusion so their scores need not share
    a scale.
    """
    if not query.strip():
        raise ValueError("Enter a query for paper retrieval.")
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if (
        publication_year_from is not None
        and publication_year_to is not None
        and publication_year_from > publication_year_to
    ):
        raise ValueError("publication_year_from cannot be later than publication_year_to")

    collection = get_collection(CHROMA_DIR)
    year_conditions = []
    if publication_year_from is not None:
        year_conditions.append({"publication_year": {"$gte": publication_year_from}})
    if publication_year_to is not None:
        year_conditions.append({"publication_year": {"$lte": publication_year_to}})
    if publication_year_to is not None and publication_year_from is None:
        year_conditions.append({"publication_year": {"$gt": 0}})
    where = (
        {"$and": year_conditions}
        if len(year_conditions) > 1
        else year_conditions[0] if year_conditions else None
    )

    corpus = collection.get(where=where, include=["documents", "metadatas"])
    ids = corpus.get("ids", [])
    documents = corpus.get("documents", [])
    metadatas = corpus.get("metadatas", [])
    total_chunks = len(ids)
    if not total_chunks:
        return []

    query_embedding = create_embeddings([query], EMBEDDING_MODEL)[0]
    dense = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(total_chunks, max(limit * 4, 20)),
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    records = {
        record_id: {
            "id": record_id,
            "text": documents[index] or "",
            "metadata": metadatas[index] or {},
        }
        for index, record_id in enumerate(ids)
    }

    fused_scores: dict[str, float] = defaultdict(float)
    matched_by: dict[str, set[str]] = defaultdict(set)
    dense_ids = (dense.get("ids") or [[]])[0]
    for rank, record_id in enumerate(dense_ids, start=1):
        fused_scores[record_id] += 1 / (RRF_CONSTANT + rank)
        matched_by[record_id].add("dense")

    query_tokens = _tokens(query)
    tokenized_documents = [_tokens(document or "") for document in documents]
    if query_tokens and tokenized_documents:
        bm25 = BM25Okapi(tokenized_documents)
        scores = bm25.get_scores(query_tokens)
        query_terms = set(query_tokens)
        lexical_order = sorted(range(len(scores)), key=lambda index: scores[index], reverse=True)
        lexical_rank = 0
        for index in lexical_order:
            if not query_terms.intersection(tokenized_documents[index]):
                continue
            record_id = ids[index]
            lexical_rank += 1
            fused_scores[record_id] += 1 / (RRF_CONSTANT + lexical_rank)
            matched_by[record_id].add("keyword")

    all_ranked_ids = sorted(fused_scores, key=fused_scores.get, reverse=True)
    # Prefer up to two chunks per paper, then use remaining slots as needed.
    # This diversifies normal results without returning too few chunks when the
    # corpus has only one matching paper.
    ranked_ids = []
    deferred_ids = []
    paper_counts: dict[str, int] = defaultdict(int)
    for record_id in all_ranked_ids:
        metadata = records[record_id]["metadata"]
        paper_id = str(metadata.get("paper_id") or record_id)
        if paper_counts[paper_id] < 2:
            ranked_ids.append(record_id)
            paper_counts[paper_id] += 1
        else:
            deferred_ids.append(record_id)
        if len(ranked_ids) >= limit:
            break
    if len(ranked_ids) < limit:
        ranked_ids.extend(deferred_ids[:limit - len(ranked_ids)])
    return [
        {
            "chunk_id": record_id,
            "text": records[record_id]["text"],
            "metadata": records[record_id]["metadata"],
            "hybrid_score": round(fused_scores[record_id], 6),
            "matched_by": sorted(matched_by[record_id]),
        }
        for record_id in ranked_ids
        if record_id in records
    ]
