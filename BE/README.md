# Inkscape AI Beta Backend

Minimal anonymous FastAPI backend for short SVG design reviews.

## Features

- Upload an SVG and get an immediate preflight report
- Follow-up chat grounded in design data and docs RAG
- Anonymous UUID sessions (no login)
- SQLite storage with 7-day auto cleanup

## Quick start

```powershell
cd BE
copy .env.example .env
# Set OPENAI_API_KEY (embeddings + default LLM) or ANTHROPIC_API_KEY with LLM_PROVIDER=anthropic

uv sync
uv run python scripts/index_corpus.py
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
| GET | `/health` | Health check |

## Environment

See [.env.example](.env.example). Key variables:

- `LLM_PROVIDER` — `openai`, `anthropic`, or `groq`
- `OPENAI_API_KEY` — required for RAG embeddings; also used when provider is openai
- `ANTHROPIC_API_KEY` — when `LLM_PROVIDER=anthropic`
- `DATA_DIR` — defaults to `./data` (SQLite, Chroma, uploaded SVGs)
- `DOCS_DIR` — defaults to `../docs`
- `SESSION_TTL_DAYS` — defaults to `7`

## Makefile

```bash
make dev           # run locally with reload
make index-corpus  # rebuild Chroma index from docs/
make lint
```

## Data layout

```
data/
  app.db          # SQLite sessions
  chroma/         # vector index
  svgs/           # uploaded SVG files
```

Sessions and SVGs are deleted automatically after `SESSION_TTL_DAYS` of inactivity.
