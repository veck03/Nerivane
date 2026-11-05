# Nerivane Project Guide

This guide describes the current application workflows and the purpose of the main project files and functions. The root [README](../README.md) is the quick-start page; this file is the longer operational and code reference.

## 1. Project at a glance

Nerivane is a React + Vite frontend backed by a FastAPI service. The service can answer questions using:

- Research papers discovered from OpenAlex, processed into text chunks, and embedded into ChromaDB.
- The configured master ocean dataset at `data/legacy_dataset/processed/ocean_q1_2020.zarr`.
- A general-answer route that does not retrieve either source.

Paper chunks, embeddings, and the metadata used by retrieval and citations live in ChromaDB. The Paper Library navigation is present in the shell but currently opens a placeholder page; there is no paper catalogue API.

```text
Browser (React/Vite)
  ├── /dashboard, /papers, and other workspace routes
  └── /api/* requests ── Vite proxy ──> FastAPI
                                      ├── /api/health
                                      └── /api/chat -> router -> source tools -> final answer
```

The frontend currently keeps conversation history in React memory for the active browser session. It is not a server-side or durable chat history.

## 2. Install and run the app

### Backend setup

From PowerShell at the project root:

```powershell
cd backend
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
uv sync
```

Set the required model configuration in `backend/.env` locally. The Groq chat client reads `GROQ_API_KEY`; `GROQ_CHAT_MODEL` is optional. `OPENALEX_API_KEY` and `MAIL_TO` are optional ingestion settings. Never commit `.env` or copy real credentials into source files.

Start FastAPI in this terminal:

```powershell
uv run python run_api.py
```

The service listens on `http://127.0.0.1:8000`. The API documentation is at `http://127.0.0.1:8000/docs`; health is at `http://127.0.0.1:8000/api/health`. On startup, FastAPI loads and warms `sentence-transformers/all-MiniLM-L6-v2`. The first model load may need network access if the model is not cached locally.

### Frontend setup

In a second terminal:

```powershell
cd frontend/react_app
npm ci
npm run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`. Vite proxies `/api` requests to FastAPI on port 8000. Use `npm run build` to build the static frontend and `npm run lint` to run Oxlint.

### Stop or restart

Press `Ctrl+C` in the corresponding terminal. Restart FastAPI after backend route or configuration changes; `run_api.py` starts Uvicorn with reload disabled. Vite normally applies frontend source changes while it is running.

## 3. Main workflows

### 3.1 Paper ingestion

The command-line settings are in `backend/run_ingestion.py`:

```powershell
cd backend
uv run python run_ingestion.py
```

Change `QUERY` and `LIMIT` in that file before a run when needed. `MAILTO` is read from the environment. Ingestion does not run automatically when FastAPI starts.

The ingestion sequence is:

1. `search_papers()` searches OpenAlex using the existing open-access/full-text filter and normalizes each work's metadata and candidate PDF URLs.
2. `run_pipeline()` checks `processed_papers.json` and ChromaDB by the OpenAlex work ID to skip work that is already indexed.
3. The existing PDF downloader reuses a local PDF or tries OpenAlex-provided links. PyMuPDF extracts page text; the chunker splits it with overlap while retaining page numbers.
4. The embedding model creates vectors and the pipeline upserts text, embeddings, and scalar metadata into the ChromaDB `research_papers` collection. The OpenAlex work ID is used as the stable chunk `paper_id`.
5. After Chroma verification, the pipeline records success in `processed_papers.json`. Missing PDFs and processing errors are recorded there with a failed status and error detail.

A failed paper can be retried on a later ingestion run. Chroma stores paper chunk text, embeddings, and chunk-level metadata for retrieval and citation creation.

### 3.2 Research Assistant chat

The frontend sends `POST /api/chat` with a JSON body containing `query`, optional paper/year settings, and `verify_citations`.

For normal Research Assistant messages:

1. `route_query()` asks the Groq model to choose exactly one route: `data`, `paper`, `both`, or `none`.
2. The coordinator `answer_query()` calls only the selected source path(s).
3. Paper questions run dense embedding search and BM25 keyword search over ChromaDB, then merge results with reciprocal-rank fusion.
4. Dataset questions call the data agent, which returns raw tool outputs. The data tools read only the master Zarr dataset and skip NaN values in calculations.
5. `synthesize_answer()` receives the route, paper chunks, raw data output, and source errors, then creates the user-facing answer. Paper citation markers are checked against the retrieved sources and their available pages.
6. The API returns the route, answer, paper sources/chunks, dataset output, warnings, and processing details in the existing response structure.

Dashboard queries select Papers, Dataset, or Both explicitly. The frontend sends an internal source directive in the query; the coordinator removes it and uses the selected route directly, so the router call is skipped for those Dashboard submissions. The Research Assistant itself continues using automatic routing.

The optional **Check claim support** control runs the citation support review when enabled for paper/both routes. It is an additional model call and should be treated as a review aid rather than proof.

### 3.3 Paper Library navigation

The `/papers` frontend route currently renders the shared placeholder. It does not call a paper list/detail endpoint. Paper evidence is still available in Research Assistant responses and the Evidence Inspector through ChromaDB retrieval results.

### 3.4 Dataset agent

The data agent is available from chat routing and as a standalone terminal program:

```powershell
cd backend
uv run python run_data_agent.py
```

Its tools describe the dataset, retrieve measurements at a nearest grid point and exact date, calculate monthly statistics, and return chart-ready multi-month or point-level daily series. The multi-month tool takes a month array and calls the existing single-month statistics function for each month; it is one data-agent tool invocation. Statistics are NaN-aware; area-wide monthly means use cosine-of-latitude weights. Daily point-series requests read one variable at one nearest grid point and are limited to 366 time steps. The code intentionally opens only the configured master dataset path in `backend/src/tools/ocean_data.py`.

### 3.5 Standalone research-agent console

For a terminal-only routed query loop:

```powershell
cd backend
uv run python run_query_agent.py
```

This uses the same route, retrieval, data, and answer functions as the API. Type `exit` or `quit` to stop.

### 3.6 Dataset inspection notebooks

Run Jupyter using the backend environment:

```powershell
cd backend
uv run jupyter lab ..\notebooks
```

`01_inspect_processed_zarr.ipynb` inspects the processed master dataset. `02_inspect_raw_netcdf.ipynb` inspects raw NetCDF files placed under the raw legacy dataset directory.

## 4. Storage and deployment

| Data | Default location | Role |
|---|---|---|
| Chroma collection | `backend/data/chroma_db/` | Paper chunk text, embeddings, and retrieval/citation metadata. |
| Downloaded PDFs | `backend/data/raw_pdfs/` | Local PDF cache used by ingestion. |
| Ingestion state | `backend/data/processed_papers.json` | Per-work status used by the ingestion pipeline. |
| Master ocean dataset | `data/legacy_dataset/processed/ocean_q1_2020.zarr` | Sole dataset opened by the ocean tools. |

ChromaDB, downloaded PDFs, the ingestion status file, and datasets are local/persistent deployment data. Keep the configured directories on persistent storage if they need to survive deployments. `CHROMA_DIR` and `RAW_PDF_DIR` are configured in `backend/src/config.py`.

## 5. File and function reference

### Root and local data

| File/path | Purpose |
|---|---|
| `README.md` | Quick start, key architecture notes, API outline, and link to this guide. |
| `.gitignore` | Excludes secrets, environments, generated artifacts, PDFs, Chroma files, and datasets. |
| `backend/.env.example` | Safe list of environment variable names and local defaults. Do not put real credentials here. |
| `backend/pyproject.toml` / `backend/uv.lock` | Python dependencies and exact resolved versions for `uv sync`. |
| `backend/data/processed_papers.json` | Ingestion status map used to skip completed work and record failures. |
| `backend/data/chroma_db/` | Persistent Chroma vector collection with embeddings, chunks, and chunk metadata. |
| `backend/data/raw_pdfs/` | Cached source PDFs. |
| `data/legacy_dataset/processed/ocean_q1_2020.zarr/` | Master ocean dataset. |
| `notebooks/01_inspect_processed_zarr.ipynb`, `notebooks/02_inspect_raw_netcdf.ipynb` | Jupyter notebooks for inspecting processed Zarr and raw NetCDF datasets. |

### Backend entry points and configuration

| File | Main functions / purpose |
|---|---|
| `backend/run_api.py` | Adds `backend/src` to imports, loads the local environment, and starts Uvicorn with `src.api.main:app`. |
| `backend/run_ingestion.py` | Defines `QUERY`, `LIMIT`, and `MAILTO`; `main()` starts `run_pipeline()`. |
| `backend/run_data_agent.py` | `main()` provides an interactive raw data-agent loop. |
| `backend/run_query_agent.py` | `main()` provides an interactive routed research-agent loop. |
| `backend/src/config.py` | Defines backend/data/PDF/Chroma/status paths and the Hugging Face embedding model. |

### Backend API

| File/function | Responsibility |
|---|---|
| `backend/src/api/main.py:lifespan()` | Loads and warms the Hugging Face embedding model at API startup. |
| `ChatRequest`, `ChatResponse` | Validate the `/api/chat` request and preserve the chat response contract. |
| `health()` | Implements `GET /api/health`. |
| `chat()` | Implements `POST /api/chat`, validates the query, calls `answer_query()`, and returns `ChatResponse`. |

### Backend agents and citations

| File/function | Responsibility |
|---|---|
| `backend/src/agents/llm.py:get_groq_chat_model()` | Creates the configured Groq-compatible `ChatOpenAI` client using environment configuration. |
| `router_agent.py:choose_query_route()` | Tool schema used to return exactly one route label. |
| `router_agent.py:route_query()` | Calls the router model and validates `data`, `paper`, `both`, or `none`. |
| `research_agent.py:_extract_source_mode()` | Removes an explicit Dashboard source directive, if present. |
| `research_agent.py:answer_query()` | Coordinates the router, paper retrieval, data agent, and final answer agent; captures per-source failures. |
| `ocean_data_agent.py:run_ocean_data_agent()` | Calls data tools over bounded tool rounds and returns raw tool outputs for final synthesis. |
| `final_answer_agent.py:synthesize_answer()` | Sends selected route and raw evidence to the model, validates citations, and optionally checks claim support. |
| `citation_engine.py:build_paper_sources()` | Groups retrieved chunks by stable paper ID and builds response-local sources, references, DOI links, and BibTeX. |
| `citation_engine.py:validate_answer_citations()` | Validates source markers and cited pages against retrieved evidence. |
| `citation_engine.py:verify_claim_support()` | Runs the optional model-based claim/evidence review. |
| `citation_engine.py:_doi_url()`, `_bibtex_escape()`, `_bibtex_key()`, `_author_names()` | Citation formatting helpers. `ClaimFinding` and `ClaimCheckResult` define the review result models. |
| `agents/__init__.py` | Exposes the public agent entry points `answer_query` and `run_ocean_data_agent`. |

### Backend ingestion

| File/function | Responsibility |
|---|---|
| `ingestion/discovery.py:search_papers()` | Searches OpenAlex, normalizes bibliographic data and candidate PDF URLs. `_abstract_from_inverted_index()` rebuilds abstracts; `_pdf_urls()` gathers unique PDF candidates. |
| `ingestion/pipeline.py:run_pipeline()` | Runs discovery results through processed-status/Chroma skip checks, PDF extraction, chunking, embeddings, and Chroma verification. |
| `ingestion/downloader.py:paper_pdf_path()` | Creates a stable cached PDF path from the paper ID. `download_pdf()` reuses local PDFs or tries OpenAlex URLs. |
| `ingestion/processing.py:extract_pages()` | Extracts non-empty page text with one-based page numbers using PyMuPDF. |
| `ingestion/chunking.py:split_pages()` | Splits each page into overlapping text chunks while preserving page numbers. |
| `ingestion/embeddings.py:_get_embedding_model()` | Caches a Hugging Face embedding model instance. `load_embedding_model()` warms it; `create_embeddings()` embeds ingestion text. |
| `ingestion/metadata.py:chunk_metadata()` | Attaches stable paper ID and bibliographic/page/chunk fields to each Chroma chunk. |
| `ingestion/__init__.py` | Package marker. |

### Backend vector storage and retrieval

| File/function | Responsibility |
|---|---|
| `database/chroma.py:get_collection()` | Opens or creates the persistent `research_papers` Chroma collection. |
| `database/repositories.py:load_status()` / `save_status()` | Read and atomically write the `processed_papers.json` status map. |
| `database/repositories.py:is_ingested()` / `store_chunks()` / `verify_chunks()` | Check indexed chunks, upsert chunk records, and verify ingestion output. |
| `retrieval/hybrid.py:_tokens()` | Tokenizes text for BM25. |
| `retrieval/hybrid.py:retrieve_paper_chunks()` | Runs dense and BM25 retrieval, merges rankings with reciprocal-rank fusion, applies year filtering, and diversifies chunks by paper. |
| `database/__init__.py`, `retrieval/__init__.py` | Package markers/public retrieval exports. |

### Backend dataset tools

| File/function | Responsibility |
|---|---|
| `tools/ocean_data.py:_open_master_dataset()` | Opens only the master Zarr path. |
| `tools/ocean_data.py:get_ocean_dataset_info()` | Returns variables, units, coordinate extents, depth levels, and time coverage. |
| `tools/ocean_data.py:get_ocean_values_at_point()` | Selects the nearest spatial grid cell for an exact date and returns available values. |
| `tools/ocean_data.py:get_monthly_statistics()` | Computes NaN-aware monthly statistics, optionally at a point/depth. |
| `tools/ocean_data.py:get_monthly_statistics_for_months()` | Takes a month array, calls `get_monthly_statistics()` for each, and returns the monthly means as chart-ready data in one data-agent tool invocation. |
| `tools/ocean_data.py:get_daily_average_series()` | Returns daily area-weighted means for a month (or selected days) as chart-ready line-series data; can instead return daily values at one selected point. |
| `tools/ocean_data.py:get_ocean_daily_series_at_point()` | Returns up to 366 daily values for one variable at the nearest grid point, preserving missing values as nulls. |
| `tools/ocean_data.py:_check_coordinates()`, `_finite_number()`, `_json_result()` | Validate spatial bounds and produce JSON-safe tool results. `OCEAN_DATA_TOOLS` is the tool list exposed to the data agent. |
| `tools/__init__.py` | Exposes the dataset tool list to the agent. |

### React frontend

| File/function | Responsibility |
|---|---|
| `frontend/react_app/src/main.jsx` | Mounts `<App />` inside React Strict Mode and imports global styles. |
| `frontend/react_app/src/App.jsx:App()` | Owns the current route, chat messages, in-memory conversations, chat requests, source selections, and evidence-inspector synchronization. |
| `App.jsx:navigate()` / `normalizePath()` | Keep the small client-side route state in sync with browser history; `/research-assistant` maps to `/`. |
| `App.jsx:startNewChat()` / `selectConversation()` | Start a blank session or restore an in-memory conversation. |
| `App.jsx:sendMessage()` / `handleSubmit()` | Send chat requests to `/api/chat`, preserve response metadata, and manage loading/errors. |
| `App.jsx:startResearchFromDashboard()` | Starts a fresh chat and passes the selected Papers/Dataset/Both mode. |
| `App.jsx:handleCitationClick()` / `selectEvidenceSource()` | Select a source/chunk and open the evidence panel when an inline citation is clicked. |
| `App.jsx:copyReferences()` / `downloadBibtex()` | Copy citations or download references in BibTeX format. |
| `App.jsx:conversationText()` / `shareConversation()` / `copyConversation()` | Share or copy the current chat transcript. |
| `components/ApplicationShell.jsx:ApplicationShell()` | Shared sidebar, navigation, conversation list, and top bar. `NavigationGroup()` renders navigation; `Icon()` renders the inline SVG icon set. |
| `components/DashboardPage.jsx:DashboardPage()` | Dashboard welcome/search, source mode, suggestions, honest resource counts, and recent in-memory conversations. `submitQuery()` sends the selected mode; `relativeTime()` and `conversationPreview()` format recent rows. |
| `components/MarkdownAnswer.jsx:MarkdownAnswer()` | Renders supported Markdown blocks and inline citation/link/formatting tokens. `resolveCitation()`, `safeHref()`, `renderInline()`, `isBlockStart()`, and `splitTableRow()` are parsing helpers. |
| `components/EvidenceInspector.jsx:EvidenceInspector()` | Right-side Sources/Dataset/Details tabs. `SourceResults()` groups papers/chunks and synchronizes citations; `DatasetResults()` shows returned dataset metadata; `OperationDetails()` shows route/status. `parseValue()`, `getToolOutputs()`, `formatValue()`, `DataField()`, and `toolLabel()` format evidence. |
| `components/DatasetCharts.jsx:DatasetCharts()` | Parses chart series returned by dataset tools and renders accessible line/bar charts as inline SVG in assistant messages. |
| `components/PlaceholderPage.jsx:PlaceholderPage()` | Empty states for workspace sections not connected to functionality yet. |
| `src/index.css`, `src/App.css` | Global tokens/reset and Research Assistant styles. |
| `components/application-shell.css` | Shared app shell and responsive sidebar/topbar styling. |
| `components/dashboard-page.css` | Dashboard layout and card styles. |
| `frontend/react_app/vite.config.js` | Vite React setup and `/api` proxy to FastAPI. |
| `frontend/react_app/package.json` / `package-lock.json` | Frontend dependencies and npm scripts (`dev`, `build`, `lint`, `preview`). |
| `frontend/react_app/index.html` | Vite HTML entry point and page metadata. |
| `frontend/react_app/public/` and `src/assets/` | Static icons and image assets. |
| `frontend/react_app/README.md` | Vite starter documentation; use the root README and this guide for current project instructions. |

## 6. Current boundaries

- Only `ocean_q1_2020.zarr` is connected to dataset tools; other datasets are not queried.
- Dashboard conversation counts and chat history are session-memory values, not persistent user records.
- The Paper Library is currently a placeholder; research-paper retrieval still works in Research Assistant.
- Projects, Shared Research, Notes, Settings, Visualizations, and Datasets navigation currently leads to placeholder content where no backend workflow is connected.
- Raw PDFs, Chroma storage, and datasets are local/persistent deployment data and should be backed up or mounted deliberately.
