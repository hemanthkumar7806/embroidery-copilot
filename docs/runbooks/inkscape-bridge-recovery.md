# Inkscape Bridge Recovery Runbook

This runbook documents long-term best practices for reliable Inkscape MCP operations.

## Default Recovery Mode

- Mode: aggressive auto-recovery
- Retry policy: up to 3 attempts
- Backoff: `250ms, 800ms, 1600ms`
- Cleanup scope: bridge-port owner + allowlisted helper processes

## What Happens Automatically

For bridge operations (`get_document_info`, `get_design_report`, `get_canvas_screenshot`, `execute_inkscape_actions`, `execute_inkscape_code`):

1. Failure is classified as one of:
   - connectivity
   - timeout
   - document context
   - unknown
2. For retriable errors, the system:
   - cleans up bridge port owner
   - cleans up allowlisted helper processes (aggressive mode)
   - reconnects bridge socket
   - rebinds document context using known document paths
   - retries with bounded backoff
3. For unknown/non-retriable errors, it fails fast with a clear message.

### User-facing behavior

- The MCP server now runs preflight checks before tool calls.
- It attempts silent recovery first (reconnect, bridge restart, document rebind).
- Only after recovery is exhausted, it returns one actionable message:
  - `Bridge is not connected. Click Restart Bridge in Inkscape.`
  - `Document is unavailable. Open your SVG and run Start MCP Server.`

## Configuration

Set these environment variables on the MCP server side:

- `INKSCAPE_RECOVERY_MAX_RETRIES` (default `3`)
- `INKSCAPE_RECOVERY_BACKOFF_MS` (default `250,800,1600`)
- `INKSCAPE_RECOVERY_MODE` (default `aggressive`)
- `INKSCAPE_RECOVERY_KILL_POLICY` (default `full_aggressive`)
- `INKSCAPE_RECOVERY_KILL_COOLDOWN_MS` (default `1200`)
- `INKSCAPE_RECOVERY_ALLOWED_PROCESS_PATTERNS` (default `inkscape-ai-bridge,inkscape_ai.bridge,start_mcp.py,inkscape-mcp`)
- `INKSCAPE_MCP_PORT` (default `9877`)
- `INKSCAPE_DOCUMENT` (recommended when running outside extension)

## Preflight Checklist

- Bridge process is running on expected host/port.
- Document path is valid from the bridge process environment.
- Inkscape and bridge run in the same filesystem context (no path translation mismatch).
- Port is not occupied by stale processes from previous sessions.

## Manual Intervention When Recovery Is Exhausted

1. Verify bridge process:
   - restart `inkscape-ai-bridge`
2. Re-establish document context:
   - open document in Inkscape and run extension, or
   - call `set_document(path)` with absolute path
3. Re-run a read-only command:
   - `get_document_info(extended=true)`
4. If still failing, inspect logs for:
   - classified error type
   - attempt count
   - recovery action taken
5. Temporarily rollback mode if needed:
   - set `INKSCAPE_RECOVERY_MODE=balanced`
   - set `INKSCAPE_RECOVERY_KILL_POLICY=port_only`

## Do Not

- Do not use broad process-kill patterns outside your approved allowlist.
- Do not use unbounded retries.
- Do not continue retrying unknown errors without checking logs.
