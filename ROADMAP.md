# StitchBase — Build Roadmap (where we are + what's next)

_The map. One focused piece per work session. Finish it, verify, then start the next._

## ✅ Where you are now (DONE + verified live)

- **Core loop works end-to-end**: detect issue → **Apply** (🟢 one-click) → value changes in
  live Inkscape → **Undo**. Proven on a real Ink/Stitch design (row spacing 0.25 → 0.4).
- Built & tested: capability tiers (🟢/🟡/🔵), fix synthesis, command queue + AI action
  history, local agent (apply/highlight/verify/undo, wrong-doc guard), tiered web report
  (Apply / Fix-all / Undo / Dismiss / Revert Batch). 28 backend tests green.
- **Architecture decided** — the 4-layer "expertise stack":
  1. **Safety rules** (universal limits — your rule engine) → 🟢
  2. **Fabric presets** (the correct value for THIS fabric)
  3. **LLM orchestrator** (judgment: reads design + fabric + image) → 🟡/🔵
  4. **RAG** (grounds advice in real docs + Q&A)

## 🎯 How we work from here

**One layer per session ("context"). Never mix.** Do it, verify it, then move on.
This is why you don't feel lost — each step is small and self-contained.

## ▶ Next steps, in order

1. **✅ DONE — Fabric presets + context**
   `fabric_presets.py` (density/pull-comp per fabric 
   
   family) + fabric-aware fix values
   in `issue_element_mapper.resolve_fix` + `POST /sessions/{id}/context` endpoint +
   a fabric picker in the report header with "ask once, remember" (localStorage).
   Verified live: unknown → 0.4mm; fleece → 0.55mm. 28 backend tests + FE build green.

2. **✅ DONE — LLM review pass (🟡/🔵)**
   `ai_review.py` (structured-first, vision-ready) + `ai_review.md` prompt +
   `POST /sessions/{id}/ai-review` (idempotent merge) + auto-trigger in the FE (non-blocking)
   + "AI reviewing…" chip + AI badge + funnel instrumentation (fix_applied / fabric_set /
   ai_review_run). Provider-agnostic (Gemini dev → Claude Sonnet for beta via env).
   Verified live: real Gemini returned 4 fabric-aware guided/recommendation findings.
   **Next upgrade:** add the rendered image (vision) — the seam is already built.

3. **✅ DONE — Rule-engine value polish (fabric-aware density detection)**
   Density band (`row_spacing_min/max_mm`) per fabric in `fabric_presets.py`; the
   `row_spacing_too_low/high` rules now detect against the fabric band (not a universal
   constant), plus a universal `DENSITY_HARD_MIN_MM` floor → critical on any fabric. Safety
   limits (widths, stitch lengths, expand) stay universal. 5 new tests (37 total).
   Verified live: 0.45mm fill is clean generically but flagged for fleece with a
   fabric-correct fix (→0.55mm).

4. **✅ DONE — RAG polish (citations on AI findings)**
   Validated the index first (`scripts/rag_benchmark.py` — 8/8 queries returned relevant
   embroidery docs). Then wired citations: the LLM cites numbered chunks via `source_refs`,
   `parse_findings` maps them to `Source`s, `RuleIssueOut.sources` + FindingsPanel show a
   "📖 Sources" list on AI findings. Robust JSON extraction + string-coercion fixes.
   Verified live: 3/3 AI findings cited (HTTP 200). 39 backend tests + FE build green.

5. **Product polish** — part 1 ✅ DONE: **Guided 🟡 Verify / re-scan loop**
   `POST /sessions/{id}/rescan` (silent re-analysis, preserves fabric + AI findings) +
   agent `_execute_rescan` (re-export live doc → upload) + a **Verify** button on
   rule-based guided findings + `verifyFinding` (re-scan → resolved / still-present).
   Verified live: a guided fix in Inkscape → Verify → the finding resolves. 40 backend
   tests + smoke + FE build green.
   ▶ **Part 2 (next):** agent **consent + apply-modes** (Ask / Auto-Safe / Auto-All).

### Fast-follow upgrades
- ✅ **DONE — Rendered image (vision)** for the LLM review. `svg_render.py` (cairosvg for
  Amazon Linux prod → Inkscape CLI for local dev, graceful fallback) renders the SVG to PNG;
  `run_ai_review` sends it as a multimodal message so the model *sees* the design (small text,
  layout, aesthetics). Verified live: Gemini accepted the image → findings. `cairosvg` in
  pyproject; **prod needs `sudo yum install -y cairo`** on Amazon Linux.

## ⚠️ Rule-engine value note (flagged, NOT urgent)

Current thresholds are hardcoded universal (e.g. `row_spacing < 0.35`). Fine as a
*safety floor*. But *optimal* density is fabric-dependent — so steps 1 & 3 make these
fabric-aware. **No change needed right now.**

## Positioning (decided)

Expert **copilot on top of Ink/Stitch** — "catch what you miss, auto-fix the safe stuff,
guide the rest, explain everything." **Not** an auto-digitizer (crowded + always needs
manual fixup). This is the "Cursor for embroidery" done right.
