"""Start a simple interactive console for the ocean data agent."""

from pathlib import Path
import json
import sys

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR / "src"))
# Load the project's environment into the process and prefer it over values
# already set in the terminal, so ChatOpenAI uses backend/.env's API key.
load_dotenv(BACKEND_DIR / ".env", override=True)

from src.agents import run_ocean_data_agent


def main() -> None:
    """Read questions until the user exits, printing each agent answer."""
    print("Ocean Data Agent — ask about ocean_q1_2020.zarr (type 'exit' to quit).")
    while True:
        question = input("\nYou: ").strip()
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue
        raw_output = run_ocean_data_agent(question)
        print(f"\nRaw data output:\n{json.dumps(raw_output, indent=2, default=str)}")


if __name__ == "__main__":
    main()
