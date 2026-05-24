# Inkscape AI — Send to AI Assistant

Minimal Inkscape extension for the **Inkscape AI beta**: one menu click uploads the current SVG to the backend and opens the chat UI in your browser.

```
Inkscape (Save) → Extensions → Inkscape AI → Send to AI Assistant
                           → POST /api/v1/sessions → open /?s=<session_id>
```

This is intentionally tiny (one `.inx` + ~120-line Python file, stdlib only). It is **not** the MCP bridge in `../inkspace-AI/` — that project is separate.

## Install

Copy both files into Inkscape's user extensions directory:

| OS      | Path                                                            |
| ------- | --------------------------------------------------------------- |
| Windows | `%APPDATA%\inkscape\extensions\InkscapeAI\`                     |
| macOS   | `~/Library/Application Support/inkscape/extensions/InkscapeAI/` |
| Linux   | `~/.config/inkscape/extensions/InkscapeAI/`                     |

Files to copy:

- `send_to_ai.inx`
- `send_to_ai.py`

Restart Inkscape. The command appears at **Extensions → Inkscape AI → Send to AI Assistant**.

## Configure

The extension talks to the backend over HTTP. By default it targets `http://localhost:8000`.

To point at a hosted instance, set the environment variable **before launching Inkscape**:

```powershell
# Windows (PowerShell, session-scoped)
$env:INKSCAPE_AI_BASE_URL = "https://your-host.example.com"
inkscape
```

```bash
# Linux / macOS
export INKSCAPE_AI_BASE_URL="https://your-host.example.com"
inkscape
```

| Variable               | Default                 | Notes                                                |
| ---------------------- | ----------------------- | ---------------------------------------------------- |
| `INKSCAPE_AI_BASE_URL` | `http://localhost:8000` | Backend root (no trailing slash). Used for both API calls and the browser URL. |

## Usage

1. Start the backend:
   ```bash
   cd BE
   uv run python -m uvicorn app.main:app --port 8000
   ```
2. Open or create an SVG in Inkscape (saving to disk is preferred but **not required** — unsaved documents are serialized from memory).
3. Run **Extensions → Inkscape AI → Send to AI Assistant**.
4. The default browser opens at `<base_url>/?s=<session_id>` with the preflight report and a chat panel.

## Troubleshooting

| Symptom                                  | Fix                                                                            |
| ---------------------------------------- | ------------------------------------------------------------------------------ |
| "Could not reach backend at …"           | Backend is not running, or `INKSCAPE_AI_BASE_URL` points at the wrong host.    |
| "Backend rejected upload (413: …)"       | SVG is over the per-session size cap (5 MB by default — see `BE/app/core/config.py:MAX_SVG_BYTES`). |
| "Backend rejected upload (400: …)"       | File extension is not `.svg`. Save the document as SVG first.                  |
| Browser did not open                     | URL is shown in the Inkscape dialog — copy it manually.                        |
| Extension not in menu                    | Files in the wrong folder, or Inkscape was not restarted after install.        |

## License

MIT.
