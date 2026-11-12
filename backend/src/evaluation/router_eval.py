"""Evaluate route selection against the curated evaluation dataset."""

import json
from pathlib import Path
from typing import Any, Callable

from agents.router_agent import route_query

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_PATH = PROJECT_ROOT / "data" / "evaluation" / "eval_dataset.json"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "backend" / "evaluation_results" / "router_eval_report.md"
ROUTE_LABELS = {"PAPER", "DATA", "BOTH", "NONE", "ABSTAIN"}
ROUTER_ROUTES = {"paper", "data", "both", "none"}


def load_evaluation_dataset(path: Path = DEFAULT_DATASET_PATH) -> list[dict[str, Any]]:
    """Read and validate the evaluation records needed by router scoring."""
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Evaluation dataset not found: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Evaluation dataset is not valid JSON: {path}: {error}") from error

    if not isinstance(records, list):
        raise ValueError("Evaluation dataset root must be a JSON array.")

    seen_ids: set[str] = set()
    for index, record in enumerate(records):
        prefix = f"Dataset record at index {index}"
        if not isinstance(record, dict):
            raise ValueError(f"{prefix} must be a JSON object.")
        for field in ("id", "question", "expected_route", "answerable"):
            if field not in record:
                raise ValueError(f"{prefix} is missing required field '{field}'.")
        if not isinstance(record["id"], str) or not record["id"].strip():
            raise ValueError(f"{prefix} has an empty or invalid 'id'.")
        record_id = record["id"].strip()
        if record_id in seen_ids:
            raise ValueError(f"Duplicate evaluation record id: {record_id}")
        seen_ids.add(record_id)
        if not isinstance(record["question"], str) or not record["question"].strip():
            raise ValueError(f"Record {record_id} has an empty or invalid 'question'.")
        if not isinstance(record["answerable"], bool):
            raise ValueError(f"Record {record_id} must have a boolean 'answerable' value.")
        if not isinstance(record["expected_route"], str):
            raise ValueError(f"Record {record_id} must have a string 'expected_route'.")
        expected_route = record["expected_route"].strip().upper()
        if expected_route not in ROUTE_LABELS:
            allowed = ", ".join(sorted(ROUTE_LABELS))
            raise ValueError(
                f"Record {record_id} has unsupported expected_route {expected_route!r}; "
                f"allowed values are {allowed}."
            )
        record["expected_route"] = expected_route
    return records


def evaluate_router(
    records: list[dict[str, Any]],
    router: Callable[[str], str] = route_query,
) -> dict[str, Any]:
    """Score answer-source routing, keeping abstention labels out of route accuracy."""
    results = []
    for record in records:
        expected = record["expected_route"]
        if expected == "ABSTAIN":
            results.append({
                "id": record["id"],
                "question": record["question"],
                "expected_route": expected,
                "answerable": record["answerable"],
                "predicted_route": None,
                "status": "abstention_case_not_scored_as_route",
                "correct": None,
                "error": None,
            })
            continue

        try:
            predicted = str(router(record["question"])).strip().lower()
            if predicted not in ROUTER_ROUTES:
                raise ValueError(f"Router returned unsupported route {predicted!r}.")
            error = None
        except Exception as exception:  # Continue the report if one model call fails.
            predicted = None
            error = f"{type(exception).__name__}: {exception}"

        correct = predicted == expected.lower() if predicted is not None else False
        results.append({
            "id": record["id"],
            "question": record["question"],
            "expected_route": expected,
            "answerable": record["answerable"],
            "predicted_route": predicted,
            "status": "scored",
            "correct": correct,
            "error": error,
        })

    scored = [item for item in results if item["status"] == "scored"]
    correct_count = sum(item["correct"] is True for item in scored)
    valid_predictions = [item for item in scored if item["predicted_route"] is not None]
    abstention_cases = [item for item in results if item["expected_route"] == "ABSTAIN"]
    return {
        "total_cases": len(results),
        "scored_cases": len(scored),
        "correct_cases": correct_count,
        "valid_predictions": len(valid_predictions),
        "failed_calls": len(scored) - len(valid_predictions),
        "accuracy": correct_count / len(scored) if scored else None,
        "valid_prediction_accuracy": (
            sum(item["correct"] is True for item in valid_predictions) / len(valid_predictions)
            if valid_predictions else None
        ),
        "route_coverage": len(valid_predictions) / len(scored) if scored else None,
        "abstention_cases": len(abstention_cases),
        "answerable_cases": sum(item["answerable"] for item in results),
        "unanswerable_cases": sum(not item["answerable"] for item in results),
        "route_counts": {
            route: sum(item["expected_route"] == route for item in scored)
            for route in ("PAPER", "DATA", "BOTH", "NONE")
        },
        "results": results,
    }


def render_router_report(summary: dict[str, Any], dataset_path: Path) -> str:
    """Format router metrics and per-question errors as a readable Markdown report."""
    accuracy = summary["accuracy"]
    accuracy_text = "N/A" if accuracy is None else f"{accuracy:.1%}"
    lines = [
        "# Router Evaluation",
        "",
        f"Dataset: `{dataset_path}`",
        "",
        "## Summary",
        "",
        f"- Total questions: {summary['total_cases']}",
        f"- Router-scored questions: {summary['scored_cases']}",
        f"- Correct routes: {summary['correct_cases']}",
        f"- Strict route accuracy (failed calls count as incorrect): {accuracy_text}",
        f"- Valid route outputs: {summary['valid_predictions']}/{summary['scored_cases']}",
        f"- Router call failures: {summary['failed_calls']}",
        "- Accuracy among valid outputs: " + (
            "N/A" if summary["valid_prediction_accuracy"] is None
            else f"{summary['valid_prediction_accuracy']:.1%}"
        ),
        "- Route coverage: " + (
            "N/A" if summary["route_coverage"] is None
            else f"{summary['route_coverage']:.1%}"
        ),
        f"- Answerable questions: {summary['answerable_cases']}",
        f"- Unanswerable questions: {summary['unanswerable_cases']}",
        f"- Abstention cases excluded from route accuracy: {summary['abstention_cases']}",
        "",
        "Expected route counts:",
        "",
        "| PAPER | DATA | BOTH | NONE |",
        "| ---: | ---: | ---: | ---: |",
        "| {PAPER} | {DATA} | {BOTH} | {NONE} |".format(**summary["route_counts"]),
        "",
    ]

    if summary["route_counts"]["BOTH"] == 0:
        lines.extend([
            "> The dataset has no BOTH examples, so this run does not measure BOTH-route accuracy.",
            "",
        ])

    incorrect = [
        item for item in summary["results"]
        if item["status"] == "scored"
        and item["predicted_route"] is not None
        and not item["correct"]
    ]
    lines.extend(["## Incorrect predictions", ""])
    if not incorrect:
        lines.append(
            "No valid route predictions were available to compare."
            if summary["valid_predictions"] == 0
            else "No incorrect predictions."
        )
    else:
        lines.extend([
            "| ID | Expected | Predicted | Question / error |",
            "| --- | --- | --- | --- |",
        ])
        for item in incorrect:
            detail = item["error"] or item["question"]
            detail = detail.replace("|", "\\|").replace("\n", " ")
            predicted = item["predicted_route"] or "ERROR"
            lines.append(
                f"| {item['id']} | {item['expected_route']} | {predicted} | {detail} |"
            )

    failures = [item for item in summary["results"] if item["error"]]
    lines.extend(["", "## Router call failures", ""])
    if not failures:
        lines.append("No router calls failed.")
    else:
        lines.extend([
            "| ID | Expected | Error |",
            "| --- | --- | --- |",
        ])
        for item in failures:
            error = item["error"].replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {item['id']} | {item['expected_route']} | {error} |")

    lines.extend(["", "## Abstention cases", ""])
    if not summary["abstention_cases"]:
        lines.append("No ABSTAIN cases in the dataset.")
    else:
        lines.extend([
            "These rows are not sent to `route_query()`: the runtime router chooses a source (`paper`, `data`, `both`, or `none`), while abstention is an end-to-end answerability behavior.",
            "",
            "| ID | Answerable | Question |",
            "| --- | --- | --- |",
        ])
        for item in summary["results"]:
            if item["expected_route"] == "ABSTAIN":
                question = item["question"].replace("|", "\\|").replace("\n", " ")
                lines.append(f"| {item['id']} | {item['answerable']} | {question} |")
    return "\n".join(lines).rstrip() + "\n"
