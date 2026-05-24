# Inkscape MCP: bridge and document path

This doc explains how the **bridge** learns which document is current and why tools can fail with "Document file not found." For quick reference, see the [Inkscape MCP README](../inkspace-AI/README.md) Troubleshooting section.

---

## How the current document is set

The bridge (e.g. `inkscape-ai-bridge`) needs a **document path** to:

- Answer `get_document_info` (path, name, dimensions, viewBox)
- Export a PNG for `get_canvas_screenshot`
- Read the SVG for `get_design_report` (and optional geometry such as node count)

That path is set in one of two ways:

1. **From Inkscape:** Open your SVG in Inkscape, then run **Extensions → Inkscape AI → Start MCP Server**. The extension writes the current document’s path into the bridge config (or starts the bridge with that path).
2. **Manually:** Set the env var `INKSCAPE_DOCUMENT` to the full path of your SVG before starting the bridge, or call the MCP tool `set_document(path)` with the full path. The bridge stores the path in its config (e.g. `~/.config/inkscape-ai/current_document`).

The bridge then uses this path for all commands that need to read or export the file.

Extended `get_document_info` also returns `document_path_source`: `env` if `INKSCAPE_DOCUMENT` is set, else `config_file` if the path comes from `current_document`.

---

## Write safety: real file first

The bridge **blocks** `execute_actions` and `execute_code` when the active path is classified as temporary or non-persisted, so the AI does not silently edit a throwaway export.

**Treated as temporary (writes blocked by default):**

- Files under the OS temp directory (e.g. `AppData\Local\Temp` on Windows)
- `temp_document.svg` inside the Inkscape-AI config directory (`~/.config/inkscape-ai/`), used only when the extension falls back for testing
- Filenames matching Inkscape extension export patterns (`ink_ext_…`)

**Bypass (testing only):** set `INKSCAPE_AI_ALLOW_TEMP_WRITES=1` on the **bridge** process, or enable **Allow temp target (testing)** in the extension (which sets that env when spawning the bridge).

**Reads** (`get_canvas_preview`, `get_document_info`, `get_design_report`) are still allowed on temp paths; check `read_only_notice` / `document_write_allowed` in `get_document_info(extended=true)`.

**Query-only actions:** `execute_actions` lists containing **only** `query-*` actions (e.g. `query-width`) are still allowed on temp paths so measurement-style calls are not blocked.

---

## Preconditions for tools to work

For `get_document_info`, `get_canvas_screenshot`, and `get_design_report` to succeed:

- The **bridge** must be running (e.g. started from the extension or by running `inkscape-ai-bridge`).
- The **document path** must be set (via extension or `set_document` / `INKSCAPE_DOCUMENT`).
- The **file must exist** and be **readable by the bridge process**: the path is resolved from the bridge’s working environment (same machine, same user, and a path the bridge can open – e.g. same drive on Windows, no WSL vs Windows path mismatch).

---

## Typical failure: "Document file not found"

You can see "Document file not found" or "No current document path set or file not found" when:

- **Path not set:** No one has set the current document (extension not run, `INKSCAPE_DOCUMENT` not set, and `set_document` not called).
- **Path not visible to the bridge:** The path is valid on your machine but the bridge runs in a different environment and cannot open that path. Examples:
  - Bridge runs in **WSL** while the path is a Windows path (e.g. `E:\user\code\...`), or the reverse.
  - Bridge runs in a **container or sandbox** with a different filesystem view.
  - **Different drive or user:** On Windows, the bridge runs under a user or drive context that doesn’t have access to the file.

**What to do:**

- Run the bridge in an environment where the document path is valid (same OS, same user, same filesystem view).
- Prefer starting the bridge from the Inkscape extension with the document already open, so the path is set correctly for that environment.
- If you use `set_document(path)` from the MCP client, use a path that the bridge process can open (e.g. an absolute path that exists from the bridge’s cwd or drive).

---

## Summary

| Requirement | Description |
|-------------|-------------|
| Bridge running | Start via **Extensions → Inkscape AI → Start MCP Server** (with “Also start the MCP bridge process”) or run `inkscape-ai-bridge` manually. |
| Document path set | Set by the extension when run from Inkscape, or via `INKSCAPE_DOCUMENT` / `set_document(path)`. |
| Path visible to bridge | The file must exist and be readable from the bridge’s process (same machine, path valid in that environment). |

For installation, configuration, and other troubleshooting, see the [Inkscape MCP README](../inkspace-AI/README.md).

---

## Current UX behavior

The MCP server is designed to auto-recover before asking users to troubleshoot:

- Runs preflight checks for bridge reachability and document context.
- Attempts silent recovery (`reconnect -> restart bridge -> reconnect -> rebind document`).
- Returns only one next-step message if recovery fails.

On Windows, when a command modifies the SVG via CLI fallback, reload the document in Inkscape to see updates.

---

## True hybrid prototype (Windows-first)

The prototype adds a session-bound live command contract:

- Session metadata: `~/.config/inkscape-ai/live_session.json`
- Command queue: `~/.config/inkscape-ai/live_commands.jsonl`
- Result files: `~/.config/inkscape-ai/live_results/<command_id>.json`

How it works:

1. Run **Extensions → Inkscape AI → Start MCP Server** to initialize `live_session.json`.
2. MCP queries `get_live_session_status` to get `session_id`.
3. MCP live tools send `live_command` payloads (`set_color`, `translate`) with that `session_id`.
4. Bridge applies action path and writes deterministic result metadata per command.

Session safety:

- `session_id` is mandatory for live commands.
- Session mismatch returns a deterministic error.
- If no live session exists, user is prompted to start from Inkscape first.

Prototype limitations:

- It is not yet a persistent in-process Inkscape daemon model.
- Apply path may use action fallback mode depending on platform/runtime capabilities.
