"""Run the router, selected retrieval paths, and final answer agent."""

from pathlib import Path
import sys

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR / "src"))
load_dotenv(BACKEND_DIR / ".env", override=True)

from src.agents import answer_query


def main() -> None:
    """Read questions and print the synthesized answer until the user exits."""
    print("Ocean Research Agent — ask a question (type 'exit' to quit).")
    while True:
        query = input("\nYou: ").strip()
        if query.lower() in {"exit", "quit"}:
            break
        if not query:
            continue
        result = answer_query(query)
        print(f"\nAssistant: {result['answer']}")


if __name__ == "__main__":
    main()
