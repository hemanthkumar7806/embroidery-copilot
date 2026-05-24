# Quick start

## 1. Install

```powershell
cd E:\user\code\MCP-chatbot\BE
uv sync
```

## 2. Configure

```powershell
copy .env.example .env
```

Edit `.env`:

- Set `OPENAI_API_KEY` (needed for embeddings and default chat model)
- Or set `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY`

## 3. Index docs (once)

```powershell
uv run python scripts/index_corpus.py
```

## 4. Run

```powershell
uv run python -m uvicorn app.main:app --reload --port 8000
```

Swagger: http://localhost:8000/docs

## 5. Test upload

```powershell
curl -X POST "http://localhost:8000/api/v1/sessions" -F "svg_file=@test-fixtures/sample.svg"
```

## Notes

- No login required — sessions are anonymous UUIDs
- SVG max size: 5 MB
- Sessions expire after 7 days of inactivity
- No PostgreSQL or Docker required for local dev
