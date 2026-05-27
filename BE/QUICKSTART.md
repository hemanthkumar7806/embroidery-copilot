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

- Set `GEMINI_API_KEY` (or another provider) for chat
- Set `LLAMA_CLOUD_API_KEY` and `LLAMA_CLOUD_PIPELINE_ID` for RAG

## 3. Test RAG (optional)

```powershell
uv run python scripts/test_llamacloud_rag.py "satin trim spacing"
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
