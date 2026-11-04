# Ocean Research frontend

React and Vite chat interface for the Ocean Research Assistant. The project overview, backend setup, environment variables, data layout, and ingestion instructions are in the [repository README](../../README.md).

## Run locally

Start the FastAPI server from `backend` first, then in this directory run:

```powershell
npm ci
npm run dev
```

The Vite development server proxies `/api` requests to `http://127.0.0.1:8000`. The chat endpoint is `POST /api/chat`.
