# Inkscape AI Beta Backend

Minimal anonymous FastAPI backend for short SVG design reviews.

## Features

- Upload an SVG and get an immediate preflight report
- Follow-up chat grounded in design data and LlamaCloud RAG
- Anonymous UUID sessions (no login)
- SQLite storage with 7-day auto cleanup

## Quick start

```powershell
cd BE
copy .env.example .env
# Set GEMINI_API_KEY (or other LLM provider) and LlamaCloud RAG vars (see below)

uv sync
uv run python scripts/test_llamacloud_rag.py "satin trim spacing"
uv run python -m uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/docs

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/sessions` | Upload SVG (multipart), returns preflight |
| GET | `/api/v1/sessions/{id}` | Session detail + chat history |
| POST | `/api/v1/sessions/{id}/chat` | Send a follow-up message |
| DELETE | `/api/v1/sessions/{id}` | Delete session |
| GET | `/health` | Health check (includes `rag` component status) |

## Environment

See [.env.example](.env.example). Key variables:

- `LLM_PROVIDER` — `openai`, `gemini`, `anthropic`, or `groq`
- `GEMINI_API_KEY` / `OPENAI_API_KEY` / etc. — for chat generation
- `LLAMA_CLOUD_API_KEY` — from [LlamaCloud](https://cloud.llamaindex.ai/) → Settings → API Keys
- `LLAMA_CLOUD_PIPELINE_ID` — your index/pipeline ID from the LlamaCloud dashboard
- `LLAMA_CLOUD_RETRIEVAL_TOP_K` — chunks per query (default `8`)
- `LLAMA_CLOUD_ENABLE_RERANKING` — `true`/`false` (default `true`)
- `DATA_DIR` — defaults to `./data` (SQLite, uploaded SVGs)
- `SESSION_TTL_DAYS` — defaults to `7`

Documents are indexed in LlamaCloud (not locally). Ensure indexing is complete in the dashboard before testing RAG.

## Makefile

```bash
make dev       # run locally with reload
make test-rag  # test LlamaCloud retrieval (optional query arg)
make lint
```

## Data layout

```
data/
  app.db          # SQLite sessions
  svgs/           # uploaded SVG files
```

Sessions and SVGs are deleted automatically after `SESSION_TTL_DAYS` of inactivity.
