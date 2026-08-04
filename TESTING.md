# StitchBase — Beta Test Guide (self-contained brief for an AI assistant)

> **How to use this file:** Paste it into ChatGPT (or any AI assistant) and say:
> *"You are helping me test this product. Walk me through Scenario 1, wait for my result,
> then continue."* The assistant has no other context — everything it needs is in this file.
>
> **Tester:** a human driving Inkscape + a browser on Windows.
> **Goal:** find bugs before a public beta. Record PASS/FAIL + notes per scenario.

---

## PART 1 — What the product is

**StitchBase** is an **AI copilot for machine-embroidery digitizers.**

**The problem:** turning artwork into a machine-embroidery design ("digitizing") is skilled,
repetitive work. Get a setting wrong — stitches too dense, a shape too thin, no underlay —
and the design fails on the machine: thread breaks, puckering, gaps. Today the only way to
catch this is a physical **test stitch-out**, which wastes time, thread and fabric.

**What we do:** the user designs in **Inkscape** (free vector editor) with the **Ink/Stitch**
plugin (free embroidery plugin). One click sends their design to us. We analyze it and return
a **report of everything likely to fail** — and for the safe, deterministic problems we can
**fix it in their live Inkscape document with one click.**

**Positioning:** a *reviewer/assistant*, **not** an auto-digitizer. It never silently takes
over. Think "spell-checker + expert second opinion," not "do it all for me."

### The three capability tiers (the core product idea)

Every finding is classified by how much we can safely automate:

| Tier | Meaning | User action |
|---|---|---|
| 🟢 **Auto Fix** | Deterministic, safe, reversible (e.g. a density number) | **Apply** button — we edit their live Inkscape doc |
| 🟡 **Guided Fix** | We know the fix but can't safely do it (needs new geometry) | We highlight + explain; user does it; then **Verify** |
| 🔵 **Recommendation** | Judgment call / design advice | Reasoning only, no automation |

Principle: **"broad analysis, selective automation."** We report *everything* we detect,
but only automate what's provably safe.

---

## PART 2 — How it works (architecture)

```
   Inkscape (user's design)
        │  ① user clicks: Extensions → Inkscape AI → Send to AI Assistant
        ▼
   Extension  ──uploads SVG──►  Backend (https://stitchbase.duckdns.org)
        │                          │  analyzes: rule engine + AI review
        │  ② also starts a         │
        │     background AGENT     ▼
        │                       Web report opens in the browser
        │                          │
        └──◄── polls for commands ─┘  ③ user clicks Apply / Verify in browser
             (agent edits the live Inkscape document)
```

**Four moving parts:**

1. **Inkscape extension** — one menu item. Uploads the design, opens the browser.
2. **Local agent** — a background process on the user's PC, started automatically by the
   extension. It polls the backend for commands and drives Inkscape via its command line
   (`inkscape --active-window --actions=...`). This is what makes "Apply" edit the *live*
   document. It exits after ~30 min idle.
3. **Backend** (FastAPI, deployed on AWS EC2 in Docker behind Caddy/HTTPS) — the brain.
4. **Web report** (React, served by the backend) — where the user reads findings and clicks
   Apply / Verify / Undo.

### What the backend actually does

- **Rule engine** — deterministic checks (density, stitch length, min widths, open paths…).
  Produces 🟢 and 🟡 findings. Fast, runs on every upload.
- **Fabric presets** — the "right" values depend on fabric. Density bands per fabric family:
  denim ~0.3–0.45mm, cotton ~0.4–0.5mm, **fleece ~0.5–0.6mm**, unknown/default 0.35–0.7mm.
  Both *detection* and the *fix value* use these.
- **AI review (LLM)** — a "senior digitizer second opinion" using **Google Gemini 2.5 Flash**.
  It reads the design data + fabric + docs **+ a rendered image of the design** (vision), and
  adds judgment findings the rules can't express. Its findings are **always 🟡/🔵, never 🟢**.
- **RAG** — an index of real embroidery documentation (Ink/Stitch, Wilcom, Hatch, community
  docs). Grounds the AI, and each AI finding shows the **sources** it relied on.

### Key technical facts (useful when debugging)

- Ink/Stitch stores settings as SVG attributes, e.g. `inkstitch:row_spacing_mm` (fill
  density — **bigger number = less dense**), `inkstitch:pull_compensation_mm`.
- 🟢 Apply works by setting those attributes on the live document. **Every Apply is a normal
  Inkscape undo step** — `Ctrl+Z` reverts it.
- The agent applies to whatever Inkscape window is **active**. It has a **wrong-document
  guard**: if the target shape isn't in the active document it refuses (safe no-op).
- Debug log on the user's PC: **`%TEMP%\inkscape_ai_debug.log`**

---

## PART 3 — Setup before testing

**Prerequisites (should already be true on the test machine):**

- Windows, **Inkscape 1.4+** installed.
- **Ink/Stitch** extension installed (Extensions menu shows an "Ink/Stitch" submenu).
- Our extension installed → **Extensions → Inkscape AI → Send to AI Assistant** exists.
- Internet access. The extension talks to **https://stitchbase.duckdns.org** by default.

**Quick sanity check before starting:**

1. Open https://stitchbase.duckdns.org/health in a browser → should show
   `{"status":"healthy", ...}`.
2. Open Inkscape → confirm both **Extensions → Ink/Stitch** and
   **Extensions → Inkscape AI** menus exist.

### ⚠️ Critical gotchas the tester MUST know

These caused confusion in earlier testing — the assistant should remind the tester:

1. **For density tests the shape must be a FILL, not a satin.**
   A shape with a **stroke (outline)** gets treated by Ink/Stitch as a **satin column**, and
   density rules won't apply. **Remove the stroke BEFORE running Ink/Stitch Params**
   (select shape → `Shift+click` the ✕ "No paint" swatch at the far left of the palette).
   If you remove the stroke *after* Ink/Stitch already tagged it as satin, the satin tag
   sticks — start with a fresh shape instead.
2. **In the Ink/Stitch Params dialog you must TICK THE CHECKBOX** next to a parameter for it
   to be written to the shape. Just typing a value isn't enough. A ✏️ pencil icon appears
   when it will be saved.
3. **Each "Send to AI" creates a NEW session** (new browser tab/URL). That's intended.
4. **The browser and Inkscape must be looking at the same design** for Apply to work. If
   several documents are open in Inkscape, click the right window first.
5. Inkscape may briefly show **"(Not Responding)"** while the Ink/Stitch Params dialog is
   open — that's normal, it recovers.

### How to create a standard test design (used by several scenarios)

> **"TEST DESIGN A"** — a too-dense fill.

1. Inkscape → **File → New**.
2. Press `R`, drag a rectangle (~5cm).
3. **Remove the stroke:** with it selected, `Shift+click` the **✕** swatch (far-left of the
   bottom colour palette). Confirm the "Stroke:" indicator (bottom-left) shows none.
4. **Path → Object to Path** (`Shift+Ctrl+C`).
5. **Extensions → Ink/Stitch → Params** → **FillStitch** tab → **tick the checkbox** next to
   **"Spacing between rows"** → set value **`0.25`** → **Apply and Quit**.
   *(0.25mm is deliberately too dense — this is the "bug" we want detected.)*
6. **Ctrl+S** → save to Desktop as `test-a.svg`.

**How to inspect a value later (two ways):**
- **Ink/Stitch Params** dialog → read "Spacing between rows".
- **XML editor** (`Ctrl+Shift+X`) → click the shape → read `inkstitch:row_spacing_mm`.

---

## PART 4 — The 11 test scenarios

For each: follow the steps, compare to **Expected**, then record **PASS / FAIL + notes**.

---

### Scenario 1 — 🟢 Density auto-fix + Undo  *(the core loop — most important)*

1. Open **TEST DESIGN A** in Inkscape (density = 0.25).
2. **Extensions → Inkscape AI → Send to AI Assistant.**
3. Browser opens with the report.
4. Find **"Row spacing too low"** under **Auto-fixable** → click **Apply**.
5. Wait ~2–5s for the button to change.
6. In Inkscape, check the value (Ink/Stitch Params or XML editor).
7. In Inkscape press **`Ctrl+Z`**. Check the value again.

**Expected:**
- Report shows a health verdict (e.g. **Caution**) and a green **Auto-fixable** section.
- The finding reads like *"Set row spacing to 0.4mm on 1 object"*.
- Apply → **"✓ Applied"**.
- Value in Inkscape changed **0.25 → 0.4**.
- `Ctrl+Z` → back to **0.25**.

---

### Scenario 2 — 🟢 Pull compensation auto-fix

1. Same design/session as Scenario 1 (or re-send).
2. Find **"Pull compensation missing"** under Auto-fixable → **Apply**.
3. Check in Ink/Stitch Params → "Pull compensation".

**Expected:** button → **Applied**; pull compensation is now a non-zero value (~0.25mm,
or the fabric-specific value if a fabric is set).

---

### Scenario 3 — 🟢 "Fix all safe issues" (batch) → Revert Batch

1. Fresh send of **TEST DESIGN A**.
2. Click the green **"Fix all safe issues (N)"** button at the top of the report.
3. Wait for all to complete; check values in Inkscape.
4. Scroll to the **"AI actions"** section at the bottom of the report → click **Revert**.
5. Check the values again.

**Expected:**
- All 🟢 findings flip to **Applied**; all values changed in Inkscape.
- A batch entry appears under "AI actions" (e.g. *"Applied 2 fixes"*).
- **Revert** restores the original values.

---

### Scenario 4 — Fabric-aware fix values  *(key differentiator)*

1. Fresh send of **TEST DESIGN A**. **Don't** apply anything yet.
2. Read the 🟢 density finding text — note the target number.
3. At the top of the report use the **Fabric** dropdown → select **Fleece**.
4. Read the same finding again.
5. (Optional) select **Cotton** and read again.

**Expected:**
- Before setting fabric: *"Set row spacing to **0.4mm**"*.
- After **Fleece**: *"Set row spacing to **0.55mm for fleece**"* — value **and** wording change.
- Cotton gives a different value again (~0.45mm).
- **Why:** fleece is high-pile so it needs *less* dense stitching than the generic default.

---

### Scenario 5 — 🟡 Guided fix → Verify → resolves

1. Create a design with an **open path**: `File → New` → press `B` (Bezier), click 3–4 points,
   press **Enter** (do **not** close the shape) → give it a fill colour → save.
   *(Alternative: a very thin/narrow filled shape.)*
2. **Send to AI Assistant.**
3. Find a 🟡 **Guided** finding (e.g. *"Open paths present"*). Click **Show** → it should select
   that shape in Inkscape.
4. Fix it in Inkscape yourself: select the path → **Path → Union** (`Ctrl++`) or use the node
   tool to close it (select both end nodes → `Ctrl+J`).
5. Back in the browser, click **Verify** on that finding.

**Expected:**
- **Show** highlights/selects the object inside Inkscape.
- **Verify** shows "Verifying…", then the finding **disappears** from the report (resolved).
- *(How it works: the agent re-exports your live document and the backend re-analyzes it.)*

---

### Scenario 6 — 🟡 Verify when NOT fixed → "Still present"

1. Same as Scenario 5, but **do not fix anything** in Inkscape.
2. Click **Verify** on the guided finding.

**Expected:** after verifying, the finding **stays**, and shows
**"Still present — re-do the step"**. (This proves Verify is genuinely re-checking, not
just marking things done.)

---

### Scenario 7 — 🔵 AI review findings with citations

1. Send any design (TEST DESIGN A is fine). Set a fabric (e.g. **Fleece**).
2. Watch the top of the report — an **"AI reviewing…"** indicator appears for a few seconds.
3. Wait for new findings to appear, tagged with a small blue **"AI"** badge.
4. Click the **chevron (⌄)** on an AI finding to expand its details.

**Expected:**
- Within ~5–30s, extra findings appear with an **AI** badge, under 🟡 Guided and/or
  🔵 Recommendations (**never** under Auto-fixable).
- Their text is fabric-aware (mentions fleece, pile, stretch, underlay…).
- Expanded details show a **📖 Sources** list (e.g. `inkstitch`, `wilcom`, `community`) —
  the documentation backing that advice.
- **Note:** AI findings are non-deterministic — exact wording differs each run. That's fine;
  we're testing that they appear, are relevant, and are cited.

---

### Scenario 8 — Vision: AI comments on tiny text

1. `File → New` → press `T`, type **"tiny text"**, set font size to something very small
   (~3–4 px so it's a few mm tall) → also draw a filled rectangle behind it.
2. Save, then **Send to AI Assistant**, set fabric.
3. Wait for the AI review, read the findings.

**Expected:** at least one AI finding refers to something **visual** — text legibility/size,
letters filling in, layout, proportions. *(This proves the AI is receiving a rendered image
of the design, not just numbers.)*
**Note:** this is the least deterministic test. If nothing about text appears, note it as an
observation rather than a hard failure — but flag it if the AI *never* mentions visual issues
across several runs.

---

### Scenario 9 — Edge case: Inkscape closed → graceful failure

1. Send a design, get the report open in the browser.
2. **Close Inkscape completely.**
3. In the browser, click **Apply** on a 🟢 finding.

**Expected:** after a short wait it shows **"Retry"** (a clear failure state) — the UI must
**not** hang forever, freeze, or crash. Reopening Inkscape with the design and clicking Retry
should then work.

---

### Scenario 10 — Edge case: wrong document active → guard blocks it

1. Send **TEST DESIGN A**; keep its report open in the browser.
2. In Inkscape, open a **different** document (`File → New`, draw something else) and make
   that the **active** window.
3. In the browser, click **Apply** on the finding from TEST DESIGN A.

**Expected:** the apply **fails safely** (**Retry**) and — most importantly — **the other
document is NOT modified**. Verify the second document is untouched.
*(This is the "wrong-document guard": it refuses when the target shape isn't in the active
document.)*

---

### Scenario 11 — New design → new session (no chat mixing)

1. Send **TEST DESIGN A** → note the browser URL (it ends with `?s=<session-id>`).
2. Create/open a **different** design → **Send to AI Assistant** again.
3. Compare the new tab's URL and contents.

**Expected:** a **new session id** and a **fresh report + fresh chat** containing only the new
design. The old design's findings/chat must **not** appear mixed in.

---

## PART 5 — How to report results

For each scenario record:

```
Scenario N: PASS / FAIL / PARTIAL
What I saw:
What I expected:
Notes (screenshots, error text, timings):
```

**If something fails, collect:**
1. The exact on-screen text/state (screenshot is ideal).
2. The browser URL (contains the session id).
3. The tail of **`%TEMP%\inkscape_ai_debug.log`** (the agent's log — this is the single most
   useful artifact for Apply/Verify failures).
4. Browser console errors (`F12` → Console).

---

## PART 6 — Known limitations (do NOT report these as bugs)

- **No rate limiting / cost cap yet** on the AI endpoints — known gap, planned before public beta.
- **AI review is non-deterministic** — different wording each run; it may occasionally return
  no findings.
- **AI findings can't be auto-fixed** — by design; they're only 🟡/🔵.
- **AI findings have generated ids**, so they have **no Verify button** (only rule-based
  guided findings do). They can be dismissed.
- **The AI review takes ~5–30 seconds** — that's expected (retrieval + LLM + image).
- **Verify only resolves rule-based findings**, not AI ones.
- Running on **Gemini 2.5 Flash** for cost reasons (not the most capable model available).
- The agent **exits after ~30 minutes idle** — if Apply stops working after a long break,
  re-run "Send to AI Assistant" to restart it.

---

## PART 7 — Guidance for the AI assistant reading this file

- Take the tester through **one scenario at a time**. Wait for their result before moving on.
- Before Scenario 1, make sure they've done the **Setup** and read the **Critical gotchas** —
  especially *fill vs satin* (remove stroke first) and *tick the checkbox in Ink/Stitch Params*.
  Most early confusion came from those two.
- When a scenario fails, **first check the gotchas** (was the shape actually a fill? was the
  right Inkscape window active? was Inkscape open?) before concluding it's a product bug.
- Distinguish **product bugs** from **test-setup mistakes** — say which you think it is.
- Keep a running PASS/FAIL tally, and at the end produce a summary table plus a prioritized
  list of the real bugs found.
