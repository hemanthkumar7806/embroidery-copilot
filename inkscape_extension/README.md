# StitchBase

_AI Design Review for Ink/Stitch_

One click from Inkscape → browser opens with your current design loaded and chat ready.

```
Extensions → StitchBase → Open in StitchBase
```

No settings dialog. No URL fields.

## Before first use

1. **Start the backend** (from `BE/`):
   ```bash
   uv run python -m uvicorn app.main:app --port 8000
   ```
2. **Build the web UI once** (from `FE/`):
   ```bash
   npm install
   npm run build
   ```
   The UI is served at `http://localhost:8000` by the backend.

## Install the extension

Copy into Inkscape's user extensions folder:

| OS      | Path                                                            |
| ------- | --------------------------------------------------------------- |
| Windows | `%APPDATA%\inkscape\extensions\InkscapeAI\`                     |
| macOS   | `~/Library/Application Support/inkscape/extensions/InkscapeAI/` |
| Linux   | `~/.config/inkscape/extensions/InkscapeAI/`                     |

Files:

- `send_to_ai.inx`
- `send_to_ai.py`

Restart Inkscape.

## What happens on click

1. Extension reads your current SVG (saved file or in-memory)
2. Uploads to `http://localhost:8000`
3. Opens `http://localhost:8000/?s=<session_id>` in your browser
4. Web app shows preview, preflight findings, and welcome chat

Re-clicking on the **same saved file** updates that session (chat history kept). A small sidecar file `your-design.svg.inkscape-ai.json` stores the session id next to the SVG.

## Troubleshooting

| Symptom | Fix |
| ------- | --- |
| "Backend is not reachable" | Start uvicorn on port 8000 |
| Browser opens but page is blank | Run `npm run build` in `FE/` |
| Still see URL / Live preview dialog | Stale extension files — recopy from repo and restart Inkscape |
| Browser did not open | Copy URL from the Inkscape message dialog |

## Advanced (optional)

Set `INKSCAPE_AI_BASE_URL` before launching Inkscape to point at a hosted backend instead of localhost.

## Smoke test

```bash
python inkscape_extension/tests/smoke_test.py
```

## License

MIT.
