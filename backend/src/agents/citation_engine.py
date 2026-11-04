"""Build verifiable paper references from retrieved chunk metadata."""

import re
import json
from collections import OrderedDict
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from agents.llm import get_groq_chat_model


_CITATION_LIKE_PATTERN = re.compile(r"\[S\d[^\[\]]*\]", re.IGNORECASE)
_SOURCE_MARKER_PATTERN = re.compile(r"\[S\d+(?:,\s*p\.?\s*\d+)?\]", re.IGNORECASE)


class ClaimFinding(BaseModel):
    claim: str
    status: Literal["supported", "unsupported", "unclear"]
    source_ids: list[str] = Field(default_factory=list)
    explanation: str


class ClaimCheckResult(BaseModel):
    findings: list[ClaimFinding] = Field(default_factory=list)


def _doi_url(doi: str) -> str | None:
    doi = (doi or "").strip()
    if not doi:
        return None
    if doi.startswith(("https://", "http://")):
        return doi
    return f"https://doi.org/{doi.removeprefix('doi:').strip()}"


def _bibtex_escape(value: str) -> str:
    return (
        value.replace("{", r"\{")
        .replace("}", r"\}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
        .replace("\\", r"\textbackslash{}")
    )


def _bibtex_key(authors: str, year: int | None, title: str, source_id: str) -> str:
    author_token = re.sub(r"[^A-Za-z0-9]", "", (authors.split(", ")[0].split()[-1:] or ["paper"])[0])
    title_token = re.sub(r"[^A-Za-z0-9]", "", title.split()[0] if title.split() else "paper")
    return f"{author_token or 'paper'}{year or 'nd'}{title_token or 'work'}{source_id}"


def _author_names(metadata: dict[str, Any]) -> list[str]:
    encoded = metadata.get("authors_json")
    if encoded:
        try:
            parsed = json.loads(encoded) if isinstance(encoded, str) else encoded
            if isinstance(parsed, list):
                return [str(name).strip() for name in parsed if str(name).strip()]
        except (TypeError, ValueError):
            pass
    authors = metadata.get("authors") or ""
    return [name.strip() for name in authors.split(", ") if name.strip()]


def build_paper_sources(paper_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group retrieved chunks by stable paper ID and attach response-local labels."""
    grouped: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for chunk in paper_chunks:
        metadata = chunk.get("metadata") or {}
        paper_id = str(metadata.get("paper_id") or chunk.get("chunk_id") or "unknown")
        source = grouped.setdefault(paper_id, {
            "paper_id": paper_id,
            "title": metadata.get("title") or "Untitled paper",
            "authors": metadata.get("authors") or "",
            "author_names": _author_names(metadata),
            "publication_year": metadata.get("publication_year") or None,
            "doi": metadata.get("doi") or "",
            "venue": metadata.get("venue") or "",
            "paper_url": metadata.get("paper_url") or "",
            "pages": [],
            "chunk_ids": [],
            "excerpts": [],
        })
        page = metadata.get("page_number")
        if page is not None:
            try:
                page = int(page)
                if page not in source["pages"]:
                    source["pages"].append(page)
            except (TypeError, ValueError):
                page = None
        chunk_id = chunk.get("chunk_id")
        if chunk_id and chunk_id not in source["chunk_ids"]:
            source["chunk_ids"].append(chunk_id)
        text = (chunk.get("text") or "").strip()
        if text:
            source["excerpts"].append({"page_number": page, "text": text})

    sources = []
    for index, source in enumerate(grouped.values(), start=1):
        source_id = f"S{index}"
        year = source["publication_year"]
        try:
            year = int(year) if year else None
        except (TypeError, ValueError):
            year = None
        source["publication_year"] = year
        source["source_id"] = source_id
        source["pages"].sort()
        source["doi_url"] = _doi_url(source["doi"])
        source["paper_url"] = (
            source["doi_url"]
            or source["paper_url"]
            or (source["paper_id"] if source["paper_id"].startswith(("https://", "http://")) else None)
        )
        author_names = source["author_names"]
        authors = "; ".join(author_names) or source["authors"] or "Unknown author"
        source["authors"] = authors
        year_label = str(year) if year else "n.d."
        reference = f"{authors} ({year_label}). {source['title']}."
        if source["venue"]:
            reference += f" {source['venue']}."
        if source["doi_url"]:
            reference += f" {source['doi_url']}"
        source["reference"] = reference

        bibtex_fields = [
            f"  title = {{{_bibtex_escape(source['title'])}}}",
            f"  author = {{{_bibtex_escape(' and '.join(author_names) if author_names else authors)}}}",
        ]
        if year:
            bibtex_fields.append(f"  year = {{{year}}}")
        if source["venue"]:
            bibtex_fields.append(f"  journal = {{{_bibtex_escape(source['venue'])}}}")
        if source["doi"]:
            bibtex_fields.append(f"  doi = {{{_bibtex_escape(source['doi'])}}}")
        source["bibtex"] = f"@article{{{_bibtex_key(authors, year, source['title'], source_id)},\n" + ",\n".join(bibtex_fields) + "\n}"
        source["cited"] = False
        source["cited_pages"] = []
        sources.append(source)
    return sources


def validate_answer_citations(
    answer: str,
    sources: list[dict[str, Any]],
    route: str,
) -> tuple[str, list[dict[str, Any]], list[str]]:
    """Remove unknown source markers and report missing or invalid citations."""
    source_by_id = {source["source_id"].upper(): source for source in sources}
    warnings: list[str] = []
    used: dict[str, set[int]] = {}

    def replace_marker(match: re.Match[str]) -> str:
        marker = match.group(0)
        parsed = re.fullmatch(r"\[(S\d+)(?:,\s*p\.?\s*(\d+))?\]", marker, re.IGNORECASE)
        if not parsed:
            warnings.append(f"Removed malformed citation {marker}.")
            return "[citation unavailable]"
        source_id = parsed.group(1).upper()
        page_text = parsed.group(2)
        source = source_by_id.get(source_id)
        if source is None:
            warnings.append(f"Removed unknown citation [{source_id}].")
            return "[citation unavailable]"
        if page_text:
            page = int(page_text)
            if page not in source["pages"]:
                warnings.append(f"Removed unsupported page number from [{source_id}, p. {page}].")
                used.setdefault(source_id, set())
                return f"[{source_id}]"
            used.setdefault(source_id, set()).add(page)
            return f"[{source_id}, p. {page}]"
        used.setdefault(source_id, set())
        return f"[{source_id}]"

    cleaned = _CITATION_LIKE_PATTERN.sub(replace_marker, answer)
    if route in {"paper", "both"} and not sources:
        warnings.append("No papers matched the selected retrieval; paper claims cannot be verified.")
    if route == "paper" and sources:
        if not used:
            warnings.append("The answer did not cite any of the retrieved papers.")
        # A lightweight coverage check for numeric claims and common claim verbs.
        sentences = re.split(r"(?<=[.!?])\s+", cleaned)
        claim_pattern = re.compile(
            r"\b(?:is|are|was|were|has|have|found|reported|shows|showed|suggests|"
            r"indicates|demonstrates|observed|measured|increased|decreased|associated)\b",
            re.IGNORECASE,
        )
        if any(
            len(sentence.split()) >= 7
            and (re.search(r"\d", sentence) or claim_pattern.search(sentence))
            and not _SOURCE_MARKER_PATTERN.search(sentence)
            for sentence in sentences
        ):
            warnings.append("Some factual statements may lack a paper citation; review their source support.")

    for source in sources:
        citation_pages = used.get(source["source_id"], set())
        source["cited"] = source["source_id"] in used
        source["cited_pages"] = sorted(citation_pages)
    return cleaned, sources, list(dict.fromkeys(warnings))


def verify_claim_support(
    answer: str,
    sources: list[dict[str, Any]],
    raw_data_output: Any = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Optionally ask the model to compare answer claims to cited excerpts.

    The result is a review aid, not a proof of factual correctness.
    """
    if not sources and raw_data_output is None:
        return [], ["Claim support check skipped because no source evidence was retrieved."]

    evidence = {
        "paper_sources": [
            {
                "source_id": source["source_id"],
                "title": source["title"],
                "venue": source["venue"],
                "pages": source["pages"],
                "excerpts": source["excerpts"],
            }
            for source in sources
        ],
        "raw_data_tool_output": raw_data_output,
    }
    verifier = get_groq_chat_model().with_structured_output(ClaimCheckResult)
    result = verifier.invoke([
        SystemMessage(content=(
            "Check factual claims in the answer against the supplied paper excerpts "
            "and, if present, the raw dataset tool output. For each meaningful factual "
            "claim, report supported only when evidence directly supports it, unsupported "
            "when evidence conflicts with or does not support it, and unclear when "
            "evidence is insufficient. Use paper source IDs and DATA for dataset output. "
            "Do not rely on outside knowledge. This is a review "
            "aid, so be conservative."
        )),
        HumanMessage(content=(
            f"Answer:\n{answer}\n\nPaper evidence (JSON):\n"
            f"{json.dumps(evidence, ensure_ascii=False, default=str)}"
        )),
    ])
    findings = result.findings if isinstance(result, ClaimCheckResult) else [
        ClaimFinding.model_validate(item) for item in result.get("findings", [])
    ]
    known_ids = {source["source_id"] for source in sources}
    if raw_data_output is not None:
        known_ids.add("DATA")
    checked = []
    warnings = []
    for finding in findings:
        valid_ids = [source_id for source_id in finding.source_ids if source_id in known_ids]
        status = finding.status
        if len(valid_ids) != len(finding.source_ids):
            status = "unclear"
            warnings.append(f"Support check returned an unknown source for: {finding.claim}")
        if status != "supported":
            warnings.append(f"{status.title()} paper support: {finding.claim}")
        checked.append({
            "claim": finding.claim,
            "status": status,
            "source_ids": valid_ids,
            "explanation": finding.explanation,
        })
    return checked, list(dict.fromkeys(warnings))
