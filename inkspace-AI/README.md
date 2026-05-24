# Inkscape MCP - Blender-style Live Connection

Inkscape MCP connects Inkscape to AI assistants (Claude, Cursor, etc.) through the Model Context Protocol (MCP), enabling visual design iteration: **see the canvas → edit → see again**.

This implementation mirrors the Blender MCP architecture: a live connection (bridge process + optional Inkscape extension), canvas capture as images, and edit tools via Inkscape actions.

## Features

- **Live connection**: Bridge process communicates with running Inkscape via DBus (Linux/macOS) or CLI (all platforms)
- **Canvas capture**: AI can see the current design as a PNG image (`get_canvas_screenshot`)
- **Document info**: Get current document path, dimensions, viewBox
- **Action execution**: Run Inkscape actions (select-all, transform-rotate, path-union, etc.) to modify the document
- **Action discovery**: List available Inkscape actions at runtime
- **Visual iteration**: Same workflow as Blender MCP - capture → edit → capture again
- **Structured diagnostics**: `get_design_report` returns Ink/Stitch elements with optional geometry (path length mm, bbox, open/closed hints, transforms, layer, visibility) and a document `summary` (counts, complexity hint, data completeness). `get_document_info(extended=True)` adds `page_size_mm`, resolved path, temp-file / write policy fields (`is_likely_temp_file`, `is_persisted_document`, `document_write_allowed`, optional `read_only_notice`, `document_path_source`). `get_design_context` returns document info + full report + `canvas_metadata` in one bridge call (no screenshot).
- **True hybrid prototype (Windows-first)**: live command session with `get_live_session_status`, `live_set_color`, and `live_translate`. Commands are session-bound and reported with command/session metadata.

## Architecture

Unlike Blender (where the addon runs inside Blender's process), Inkscape extensions run as separate processes. So the "live" side is implemented as:

1. **Bridge** (`inkscape-ai-bridge`): Standalone TCP server that talks to Inkscape via DBus (Linux/macOS) or CLI (Windows/fallback)
2. **MCP Server** (`inkscape-ai`): Exposes MCP tools to the AI; connects to the bridge over TCP
3. **Inkscape Extension** (optional): "Start MCP Server" menu item that writes the current document path and optionally spawns the bridge

```
AI → MCP Server → Bridge → Inkscape (DBus/CLI)
```

Hybrid prototype command flow:

```
AI → MCP live tool → Bridge live_command → action apply + result record
```

## Installation

### Prerequisites

- Inkscape installed and available in PATH (or set `INKSCAPE_BIN` env var)
- Python 3.10+
- For DBus support on Linux/macOS: `PyGObject` (install via `pip install PyGObject` or system package manager)

### Install the Package

```bash
# Using uv (recommended)
uv pip install -e .

# Or using pip
pip install -e .
```

This installs:
- `inkscape-ai` - MCP server command
- `inkscape-ai-bridge` - Bridge server command

### Install the Inkscape Extension (Optional)

1. Copy the `inkscape_extension/` folder to your Inkscape extensions directory:
   - Linux: `~/.config/inkscape/extensions/InkscapeAI/`
   - macOS: `~/Library/Application Support/Inkscape/extensions/InkscapeAI/`
   - Windows: `%APPDATA%\Inkscape\extensions\InkscapeAI\`

2. Copy both files:
   - `start_mcp.inx`
   - `start_mcp.py`

3. Restart Inkscape

4. The extension will appear under **Extensions → Inkscape AI → Start MCP Server**

## Configuration

### Environment Variables

**Bridge configuration:**
- `INKSCAPE_MCP_HOST`: Bridge host (default: `localhost`)
- `INKSCAPE_MCP_PORT`: Bridge port (default: `9877`)
- `INKSCAPE_DOCUMENT`: Current document path (set automatically by extension, or manually)
- `INKSCAPE_BIN`: Path to Inkscape executable (if not in PATH)
- `INKSCAPE_MCP_ALLOW_ALL_ACTIONS`: Set to `1`/`true`/`yes` to allow all actions (default: allowlist only)
- `INKSCAPE_AI_CONFIG_DIR`: Config directory (default: `~/.config/inkscape-ai`)
- `INKSCAPE_AI_ALLOW_TEMP_WRITES`: Set to `1`/`true`/`yes` to allow MCP **write** tools (`execute_inkscape_actions`, `execute_inkscape_code`) on temporary paths (default: off; use for testing only). The Inkscape extension can set this when **Allow temp target (testing)** is enabled.

**MCP Server configuration:**
- `INKSCAPE_MCP_HOST`: Bridge host (default: `localhost`)
- `INKSCAPE_MCP_PORT`: Bridge port (default: `9877`)
- `INKSCAPE_RECOVERY_MODE`: Recovery mode (`aggressive` or `balanced`, default: `aggressive`)
- `INKSCAPE_RECOVERY_MAX_RETRIES`: Auto-recovery retries for bridge operations (default: `3`)
- `INKSCAPE_RECOVERY_BACKOFF_MS`: Retry backoff sequence in ms (default: `250,800,1600`)
- `INKSCAPE_RECOVERY_KILL_POLICY`: Cleanup policy (`port_only` or `full_aggressive`, default: `full_aggressive`)
- `INKSCAPE_RECOVERY_KILL_COOLDOWN_MS`: Minimum interval between cleanup actions (default: `1200`)
- `INKSCAPE_RECOVERY_ALLOWED_PROCESS_PATTERNS`: Allowlisted helper-process patterns for aggressive cleanup

### Action Allowlist

By default, only safe actions are allowed (e.g. `select-*`, `path-*`, `transform-*`, `export-*`). To allow all actions:

```bash
export INKSCAPE_MCP_ALLOW_ALL_ACTIONS=1
```

## Usage

### Starting the Bridge

**Option 1: From Inkscape Extension (Recommended)**
1. **Save your design as a `.svg`** (real path, not only an unsaved window)
2. Go to **Extensions → Inkscape AI → Start MCP Server**
3. Check "Also start the MCP bridge process" (default: enabled)
4. The bridge starts with that file path. If the document was never saved, the extension asks you to save first unless you enable **Allow temp target (testing)** (writes then use a config-dir copy and require the allow-temp env).

### Real file first (recommended)

- **Read** tools (`get_canvas_screenshot`, `get_design_report`, `get_document_info`) still work if the bridge points at a temp/export path.
- **Write** tools are **blocked** when the path looks temporary (`AppData\\Local\\Temp`, `temp_document.svg` in the Inkscape-AI config dir, or `ink_ext_*` exports). This avoids editing the wrong file silently.
- Use `get_document_info(extended=True)` and check `is_persisted_document` / `document_write_allowed` before asking the AI to modify the design.
- After CLI-based edits on Windows, reload the SVG in Inkscape. Successful tool results include `refresh_result` (`live_via_dbus` vs `manual_reload_suggested`) and a `reload_hint` when relevant.

**Option 2: Manual Start**
```bash
# Set current document (or extension will set it)
export INKSCAPE_DOCUMENT="/path/to/your/document.svg"

# Start bridge
inkscape-ai-bridge
```

The bridge listens on `localhost:9877` by default.

### Configuring MCP Client

#### Claude Desktop

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "inkscape-ai": {
      "command": "uvx",
      "args": ["inkscape-ai"]
    }
  }
}
```

Or using `uv` directly:

```json
{
  "mcpServers": {
    "inkscape-ai": {
      "command": "python",
      "args": ["-m", "inkscape_ai.server"]
    }
  }
}
```

#### Cursor

Add to `.cursor/mcp.json` or Settings > MCP:

```json
{
  "mcpServers": {
    "inkscape-ai": {
      "command": "uvx",
      "args": ["inkscape-ai"]
    }
  }
}
```

### Using with AI

Once the bridge is running and the MCP server is configured:

1. **Capture the canvas**: AI calls `get_canvas_screenshot()` to see the current design
2. **Get document info**: AI calls `get_document_info()` for path, dimensions, etc.
3. **List actions**: AI calls `action_list()` to discover available Inkscape actions
4. **Edit**: AI calls `execute_inkscape_actions(["select-all", "transform-rotate:90"])` to modify the document
5. **Iterate**: AI captures again to see the result

### True Hybrid Prototype

Available MCP tools:

- `get_live_session_status()` - Returns active live `session_id`, lock status, and bound document path.
- `live_set_color(element_id, color, mode="fill")` - Applies color update for a target element id.
- `live_translate(element_id, dx, dy)` - Applies translation for a target element id.

Prototype behavior:

- Session is created by **Start MCP Server** and stored in config (`live_session.json`).
- Bridge validates `session_id` before applying live operations.
- Bridge stores command/result artifacts (`live_commands.jsonl`, `live_results/<command_id>.json`) for deterministic status reporting.
- Live apply mode is DBus when available; otherwise falls back to bridge action execution path.

**Example AI workflow:**
```
1. get_canvas_screenshot() → See current design
2. execute_inkscape_actions(["select-all", "object-rotate-90-cw"]) → Rotate all objects
3. get_canvas_screenshot() → See updated design
```

## Platform Notes

### Linux/macOS (DBus)

- Bridge uses DBus to send actions directly to the running Inkscape instance
- Changes appear immediately in Inkscape (no reload needed)
- Requires Inkscape 1.2+ with DBus support

### Windows (CLI Fallback)

- Bridge uses Inkscape CLI (`--actions=... --batch-process`) to modify files on disk
- **Important**: After AI edits, use **File → Reload** in Inkscape to refresh from disk
- Tool results include `reload_hint`, `target_path`, and `refresh_result` (`manual_reload_suggested` when a reload is needed)
- In the hybrid prototype, live operations may report `apply_mode=cli_fallback` when DBus live apply is unavailable.

## Troubleshooting

### Bridge won't start

- Check Inkscape is installed: `inkscape --version`
- Set `INKSCAPE_BIN` if Inkscape is not in PATH
- Check port 9877 is not in use: `netstat -an | grep 9877` (Linux/macOS) or `netstat -an | findstr 9877` (Windows)

### "No current document path set" / "Document file not found"

Tools like `get_document_info`, `get_canvas_screenshot`, and `get_design_report` require the **bridge** to see the current document: the bridge must run on the same machine where the file lives, and the path must be valid from the bridge’s process.

- **Set the current document:** Run **Extensions → Inkscape AI → Start MCP Server** from Inkscape (with the document open), or call `set_document(path)` with the full path to your SVG.
- **If you still get "Document file not found":** The bridge may be running in a different environment (e.g. different drive, WSL, or container) where that path is not visible. Run the bridge in an environment where the document path is valid, or use a path the bridge can read (e.g. same drive and user).

For more detail, see [Bridge and document path](../docs/inkscape-bridge-setup.md) in the docs.
For operations and recovery flow, see [Inkscape bridge recovery runbook](../docs/runbooks/inkscape-bridge-recovery.md).

The MCP server will attempt silent auto-recovery first. If recovery is exhausted, it should return a single actionable step instead of raw internal errors.

### Actions fail with "not allowed"

- Check the action is in the allowlist (see `SAFE_ACTIONS` in `bridge_config.py`)
- Or set `INKSCAPE_MCP_ALLOW_ALL_ACTIONS=1` to allow all actions

### DBus not working (Linux/macOS)

- Ensure Inkscape 1.2+ is running
- Check DBus is available: `dbus-send --session --print-reply --dest=org.freedesktop.DBus /org/freedesktop/DBus org.freedesktop.DBus.ListNames`
- Bridge falls back to CLI automatically if DBus fails

### Extension not appearing in Inkscape

- Check files are in the correct extensions directory
- Ensure `.inx` and `.py` files are in the same folder
- Restart Inkscape
- Check Inkscape's extension error log (Help → System Information → Extensions)

## Development

### Project Structure

```
inkspace-AI/
├── src/inkscape_ai/
│   ├── __init__.py
│   ├── server.py                 # MCP server (tools, connection to bridge)
│   ├── bridge.py                 # Bridge TCP server (command handlers)
│   ├── design_report_extract.py  # Ink/Stitch report + document summary (no AI)
│   ├── bridge_config.py          # Config: document path, allowlist
│   └── inkscape_cli.py           # Inkscape CLI runner (subprocess)
├── inkscape_extension/
│   ├── start_mcp.inx      # Extension descriptor
│   └── start_mcp.py       # Extension script
├── pyproject.toml
└── README.md
```

### Running Tests

```bash
# Test bridge
python -m inkscape_ai.bridge

# Test MCP server (requires bridge running)
python -m inkscape_ai.server
```

## License

MIT License

## Acknowledgments

- Architecture inspired by [Blender MCP](https://github.com/ahujasid/blender-mcp)
- Inkscape CLI patterns from [inkscape-mcps](https://github.com/yourusername/inkscape-mcps) (reference only)
