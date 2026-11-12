"""Run the router evaluation and write a Markdown report."""

import argparse
from pathlib import Path
import sys

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR / "src"))
load_dotenv(BACKEND_DIR / ".env", override=True)

from src.evaluation.router_eval import (  # noqa: E402
    DEFAULT_DATASET_PATH,
    DEFAULT_REPORT_PATH,
    evaluate_router,
    load_evaluation_dataset,
    render_router_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Nerivane route selection.")
    parser.add_argument(
        "--dataset", type=Path, default=DEFAULT_DATASET_PATH,
        help="Path to eval_dataset.json.",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_REPORT_PATH,
        help="Markdown report path.",
    )
    args = parser.parse_args()

    records = load_evaluation_dataset(args.dataset)
    summary = evaluate_router(records)
    report = render_router_report(summary, args.dataset)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(report)
    print(f"Report written to: {args.output}")


if __name__ == "__main__":
    main()
