# Embroidery digitizing + AI: current tools vs what’s missing

Audit from the perspective of an **embroidery digitizer** who wants to use AI in the workflow. Covers: what works today (Inkscape, SVG, PES, DST, etc.), what’s missing, and what to add for full-fledged AI-assisted digitizing.

---

## 1. Current tools (what you have)

### 1.1 Inkscape MCP (user-inkscape-ai / inkspace-AI)

| Tool | What it does | File types |
|------|----------------|------------|
| `get_canvas_screenshot` | Capture current document as PNG so AI can “see” the design | **SVG only** (current Inkscape doc) |
| `get_document_info` | Get document path, name, width, height, viewBox | **SVG only** |
| `set_document` | Tell the bridge which document is current (path) | **SVG only** |
| `execute_inkscape_actions` | Run Inkscape actions (e.g. select-all, transform-rotate:90, export-*) | **SVG only** |
| `action_list` | List available Inkscape actions for use with execute_inkscape_actions | — |
| `execute_inkscape_code` | Run Python in Inkscape with `inkex`, `doc`, `root` (SVG DOM) | **SVG only** |

- **Works with:** Only the **current document in Inkscape**, which must be **SVG**.
- **Does not:** Open PES, DST, or EMB; run Ink/Stitch extensions by name; set Ink/Stitch params via a dedicated tool.

### 1.2 Inkscape MCP (inkscape-mcps, if enabled)

| Tool | What it does | File types |
|------|----------------|------------|
| `action_list` / `action_run` | Run Inkscape CLI actions on a file (e.g. export PNG) | Files in **INKS_WORKSPACE** (typically SVG) |
| `dom_validate` | Validate SVG structure | SVG |
| `dom_set` | Set attributes/styles with CSS selectors (e.g. set `inkstitch:row_spacing_mm` on elements) | SVG in workspace |
| `dom_clean` | Clean/optimize SVG (e.g. scour) | SVG |

- **Works with:** SVG files inside the configured workspace path.
- **Does not:** Open or edit PES/DST/EMB; run Ink/Stitch menus; export to embroidery formats.

### 1.3 Workspace / docs (no MCP)

- **design (14).pes** in `inkscape-workspace`: exists, but **binary** — no tool can read or edit stitch data or “params” inside it.
- **Docs:** Ink/Stitch, Wilcom, Hatch, Embird, Ricoma, community (density, underlay, pull comp, failure causes). Used by AI for advice and validation rules, not as “tools” that act on files.

---

## 2. File formats: what can do what

| Format | Inkscape opens? | Ink/Stitch edits? | MCP can act on? | Notes |
|--------|------------------|-------------------|------------------|--------|
| **SVG** | Yes | Yes (with inkstitch:* params) | Yes (screenshot, info, actions, code, DOM) | Only format that is “full” for AI + Inkscape. |
| **PES** | No | No (export only) | No (binary; read not supported) | Stitch-only; no density/underlay in file. |
| **DST** | No | No (export only) | No (binary) | Same as PES. |
| **EMB / JEF / etc.** | No | No | No | Stitch or proprietary; not in this stack. |

So for **doing actions** (view, edit, validate, export):

- **SVG:** full support (view, edit via actions/code/DOM, then export from Inkscape/Ink/Stitch).
- **PES, DST, etc.:** no “open and edit” in this stack; they are **output-only** here. To “fix” them you’d need to edit the **source** (e.g. SVG in Inkscape) and re-export.

---

## 3. What an embroidery digitizer would expect (workflow)

Typical expectations for a **full-fledged digitizing + AI** setup:

| Step | Expectation | Current state |
|------|-------------|----------------|
| **Import** | Open image/vector (SVG) or stitch file (PES/DST) to work on | SVG: yes (Inkscape). PES/DST: **no** (no import/conversion). |
| **See design** | AI (or user) sees current design | Yes: `get_canvas_screenshot` + `get_document_info` for **SVG**. |
| **Assign stitch types** | Set fill / satin / run per object | No dedicated tool. Possible via `execute_inkscape_code` (inkex + inkstitch) or `dom_set` (if SVG in workspace). |
| **Set params** | Density, underlay, pull comp, stitch length, etc. | No “set_density(path, value)” tool. Possible via code (inkex) or DOM (dom_set) on SVG. |
| **Validate** | Run something like “Troubleshoot” and get errors/warnings | No “run_troubleshoot” tool. Could be done via code if Ink/Stitch extension is callable. |
| **Stitch order / pathing** | Reorder objects, minimize jumps | No dedicated tool. Inkscape actions (e.g. order) + code possible. |
| **Export** | Export to PES, DST, JEF for the machine | No “export_to_pes(path)” MCP tool. Inkscape/Ink/Stitch does it from UI (or CLI if available). |
| **Read stitch files** | From PES/DST: stitch count, colors, bounds | No tool; files are binary. |
| **Fabric / presets** | Apply or suggest fabric presets | Only in docs; no tool that “applies” to a file. |

So: the only format on which we can do **concrete actions** today is **SVG** in Inkscape; for PES/DST we have no import, no edit, no structured read.

---

## 4. Items that are missing (for full AI-assisted digitizing)

### 4.1 Format and import

- **Import PES / DST / EMB**  
  - No tool or Inkscape path to open or convert these into an editable format (e.g. SVG with stitch objects).  
  - **To add:** Converter (e.g. stitch → SVG outline/objects) or integration with an app that can open PES/DST and export SVG/editable format.

- **Read PES/DST metadata**  
  - No “get_stitch_count”, “get_color_list”, “get_bounds” from .pes/.dst.  
  - **To add:** A small library or script that parses PES/DST (or uses an existing one) and exposes stitch count, color stops, size, etc., so AI can reason about the file without opening it in Inkscape.

### 4.2 Inkscape + Ink/Stitch actions

- **Ink/Stitch-specific MCP tools**  
  - No direct “run Params”, “run Troubleshoot”, “run Export” from MCP.  
  - **To add:** Either dedicated MCP tools that call Ink/Stitch extensions (e.g. `run_inkstitch_troubleshoot`, `run_inkstitch_export_pes`), or document how to do it via `execute_inkscape_code` / CLI so AI can use it reliably.

- **Set embroidery params from AI**  
  - No simple “set_density”, “set_underlay”, “set_pull_comp” API.  
  - **To add:** Wrapper tools or shared scripts that take (file path or current doc, element selector or id, param name, value) and set `inkstitch:*` attributes (via `execute_inkscape_code` or `dom_set`), so AI can “fix” designs without writing raw inkex.

- **Export to machine format from MCP**  
  - No “export_current_document_to_pes(path)” (or DST, etc.).  
  - **To add:** Check if Ink/Stitch supports export via Inkscape CLI or extension API; if yes, add an MCP tool or a script that the AI can call.

### 4.3 Validation and reporting

- **Structured “design report”**  
  - No tool that returns “list of elements with stitch type and key params” (density, underlay, pull comp) for the current SVG.  
  - **To add:** Script or MCP tool (using `execute_inkscape_code` + inkex to traverse document and read `inkstitch:*`) that returns a JSON/markdown summary so AI can validate against your rules (density, underlay, pull comp, etc.).

- **Run Troubleshoot and get results**  
  - No automated way to run Ink/Stitch Troubleshoot and get errors/warnings back into the AI.  
  - **To add:** MCP tool or script that runs Troubleshoot (or equivalent checks), then parses the result (or a generated report layer) and returns a structured list of issues.

### 4.4 Workflow and UX

- **“Current document” vs workspace file**  
  - Inkscape MCP works on “current document” (often a temp SVG). Workspace has `design (14).pes` and SVGs.  
  - **To add:** Clear convention or tool: e.g. “save current as inkscape-workspace/design_name.svg” so AI and tools always have a stable path; and/or a tool that “loads” a workspace SVG into Inkscape so the bridge points at it.

- **Fabric presets / design notes**  
  - Presets and rules live in docs only.  
  - **To add (optional):** Config or small “design brief” (fabric, target machine, preset name) that AI uses when suggesting or applying params (e.g. “cotton”, “fleece”), and optionally store in the project or in the SVG.

---

## 5. Summary: what you have vs what you need

| Area | Have | Missing |
|------|------|--------|
| **View design** | Screenshot + doc info for **SVG** in Inkscape | Same for PES/DST (would need renderer or converter) |
| **Edit SVG** | Actions, code (inkex), DOM (dom_set) | Convenience tools: set_density, set_underlay, set_pull_comp |
| **Edit PES/DST** | Nothing | Import or convert to SVG; or read-only metadata (stitch count, colors) |
| **Validate** | Docs + manual Troubleshoot | MCP “run_troubleshoot” + structured “design report” (elements + params) |
| **Export** | Manual from Inkscape/Ink/Stitch | MCP “export_to_pes” / export_to_dst (if Ink/Stitch supports CLI) |
| **File scope** | Current Inkscape doc (SVG) + workspace files | Clear link between “current design” and a workspace path (e.g. one canonical SVG per design) |

So: **for SVG in Inkscape you have the base** (see, run actions, run code, and with inkscape-mcps set DOM). **For PES/DST and for a smooth “digitizer + AI” workflow you’re missing:** import/convert or metadata read, Ink/Stitch-specific tools (params, troubleshoot, export), and a structured way to get “what’s in this design” and “what’s wrong” so the AI can plan and act.

---

## 6. Suggested order to implement (for AI-assisted digitizing)

1. **Structured design report** (SVG): script or MCP tool that, given an SVG path (or current doc), returns elements + stitch types + key inkstitch params. Enables AI to “understand” the design and suggest fixes.
2. **Set params from AI**: wrapper(s) that set density/underlay/pull comp (and optionally stitch type) on selected elements via `execute_inkscape_code` or `dom_set`, so AI can apply fixes without writing raw inkex.
3. **Run Troubleshoot and return results**: automate Ink/Stitch Troubleshoot and parse results into a list of issues the AI can use.
4. **Export to PES/DST**: if Ink/Stitch allows, add an MCP tool or script to export current document to a given path (e.g. `inkscape-workspace/design 14.pes`).
5. **PES/DST metadata reader**: small script or lib to read stitch count, colors, bounds from .pes/.dst so AI can talk about “design (14).pes” even when not editing it.
6. **Import PES/DST → editable**: optional; only if you need to “fix” existing stitch files by converting to SVG (e.g. via third-party converter or Ink/Stitch if it ever adds import).

This gives you a clear picture of **current tools**, **what works with SVG vs PES/DST**, and **what’s missing** so you can plan full-fledged embroidery development and where to plug in the AI.
  