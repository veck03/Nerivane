# Nerivane — Ocean Research Assistant

A local research assistant for querying the ocean Q1 2020 master dataset and an indexed collection of research papers. A Groq-backed router selects `data`, `paper`, `both`, or `none`. Paper retrieval combines local Hugging Face embeddings and BM25 keyword search; data questions use tools over the master Zarr dataset.

For the full workflow walkthrough and file/function reference, see [the project guide](docs/PROJECT_GUIDE.md).

## How a chat request works

1. The React app sends a question to FastAPI.
2. The router makes one Groq call and selects a route.
3. The selected source agents run:
   - `data` or `both`: the ocean data agent chooses and calls Python data tools.
   - `paper` or `both`: the query is embedded locally and hybrid retrieval returns paper chunks. Optional publication-year filters apply here.
   - `none`: no data or paper retrieval runs.
4. The final answer agent makes one Groq call with the route and gathered context.
5. The backend validates paper source labels and page numbers, builds references, and returns the answer and sources.
6. If **Check claim support** is enabled, another Groq call compares claims with retrieved evidence. It is a review aid, not proof.

Paper citations use response-local labels such as `[S1, p. 4]`, mapped to stable paper IDs. The chat shows paper details and excerpts, links to available DOI or landing pages, and can copy references or download BibTeX.

Dataset trend queries can return chart-ready monthly means for Q1 or daily values at a selected grid point. When those tools return a series, the chat renders it as a lightweight inline SVG bar or line chart. Missing observations remain gaps; no chart is shown when a tool returns only a single statistic or point value.

## LLM call counts

These are logical Groq model invocations per question, not counting transient HTTP retries. Local Hugging Face embeddings, Chroma/BM25 retrieval, Python data tools, citation validation, and reference formatting do not call an LLM.

| Route | Calls without optional claim check | Notes |
|---|---:|---|
| `none` | 2 | One router call and one final-answer call. |
| `paper` | 2 | One router call and one final-answer call. If claim checking is enabled and paper sources exist, add 1. |
| `data` | 3–6 | Router 1 + data agent 1–4 + final answer 1. |
| `both` | 3–6 | Router 1 + data agent 1–4 + final answer 1. Claim checking adds 1 when enabled and paper sources or a data-agent result are present. |

The data agent can select several Python tools during one model turn; those tool executions are not additional LLM calls. It allows up to three tool-producing rounds. It may make a fourth model call to decide it is finished or hit the round limit, so the maximum is four data-agent calls. The optional support check only runs on `paper` and `both` routes. It adds one call when paper sources or a data-agent result are present; it is skipped when there are no paper sources and `raw_data_output` is `None`.

Dashboard source selection explicitly chooses Papers, Dataset, or Both, so that path skips the router call. Papers then uses one final-answer call; Dataset uses one to four data-agent calls plus one final call; Both adds paper retrieval locally and follows the Dataset call count. Normal Research Assistant chat uses automatic routing.

## Project layout

```text
backend/                 FastAPI app, agents, ingestion, and data tools
docs/                    Detailed workflows and file/function reference
data/                    Local ocean datasets (ignored by Git)
frontend/react_app/      React + Vite chat frontend
notebooks/               Dataset inspection notebooks
```

The ocean data tools read only:

```text
data/legacy_dataset/processed/ocean_q1_2020.zarr
```

Raw NetCDF files for inspection can be placed under `data/legacy_dataset/raw/`. The dataset, downloaded PDFs, Chroma database, and ingestion state are local generated/user data and are not included in Git.

## Requirements

- Python 3.14 or newer
- [uv](https://docs.astral.sh/uv/)
- Node.js and npm
- A Groq API key
- The master Zarr dataset for ocean data questions

## Configure and install the backend

From PowerShell:

```powershell
cd D:\Projects\Nerivane\backend
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Edit `backend/.env` locally and set `GROQ_API_KEY`. `GROQ_CHAT_MODEL` is optional; the configured default is `openai/gpt-oss-120b` on Groq. `OPENALEX_API_KEY` and `MAIL_TO` are optional for OpenAlex ingestion. Never commit `.env` or put actual keys in source files. The root `.gitignore` ignores `.env` and keeps `.env.example`.

Install the Python dependencies:

```powershell
uv sync
```

## Start the application

Start the backend in one terminal:

```powershell
cd D:\Projects\Nerivane\backend
uv run python run_api.py
```

FastAPI listens at `http://127.0.0.1:8000`. The API docs are at `http://127.0.0.1:8000/docs`; health check is `http://127.0.0.1:8000/api/health`.

At startup, FastAPI loads and warms `sentence-transformers/all-MiniLM-L6-v2` before accepting requests. The first startup downloads the model if it is not in the Hugging Face cache, so it may take longer and needs network access. After startup, paper-query embeddings reuse the in-memory model.

Start the frontend in a second terminal:

```powershell
cd D:\Projects\Nerivane\frontend\react_app
npm ci
npm run dev
```

Open the Vite URL printed in the terminal, usually `http://localhost:5173`. Vite proxies `/api` requests to the FastAPI server at `127.0.0.1:8000`. Run `npm ci` when setting up or refreshing dependencies; start the frontend with `npm run dev`.

## Chat API

`POST /api/chat` accepts a JSON request such as:

```json
{
  "query": "What do the papers say about ocean temperature profiles?",
  "paper_limit": 5,
  "publication_year_from": 2018,
  "publication_year_to": 2024,
  "verify_citations": false
}
```

The year fields are optional and filter paper retrieval. `verify_citations` is optional and defaults to `false`; setting it to `true` may add one Groq call when there is evidence to check. The response includes the selected route, answer, retrieved paper chunks and grouped references, source errors, citation warnings, and optional claim-check findings.

## Ingest papers

From `backend`, edit `QUERY` and `LIMIT` in `run_ingestion.py` if needed, then run:

```powershell
uv run python run_ingestion.py
```

OpenAlex search filters for works marked open access with full text available. The downloader tries OpenAlex-provided PDF URLs; some papers may still have no accessible direct PDF. PDFs are saved in `backend/data/raw_pdfs/`. Extracted chunks and embeddings are stored in the local Chroma database at `backend/data/chroma_db/`, with progress recorded in `backend/data/processed_papers.json`. The Paper Library navigation currently opens a placeholder page; indexed papers remain available to the Research Assistant through retrieval.

## Other commands

Run the interactive research agent:

```powershell
cd D:\Projects\Nerivane\backend
uv run python run_query_agent.py
```

Run the raw ocean data agent:

```powershell
uv run python run_data_agent.py
```

Open the dataset inspection notebooks using the backend environment:

```powershell
uv run jupyter lab ..\notebooks
```

## Retrieval and citation notes

- Dense paper retrieval uses the same local MiniLM model used during ingestion; BM25 keyword ranks are fused with dense results.
- Retrieval prefers up to two chunks per paper, then fills remaining result slots when fewer papers are available.
- Citation labels and page numbers are checked against the retrieved chunks. This catches unknown labels and pages but does not prove that an excerpt supports a claim.
- The optional claim-support check asks the Groq model to classify claims as supported, unsupported, or unclear. Treat this as a review aid.
- Newly ingested chunks store structured author names, venue, and landing-page URL. Existing chunks without those fields fall back to their previously stored metadata, DOI, or OpenAlex work URL.
