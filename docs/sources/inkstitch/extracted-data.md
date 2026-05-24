# Ink/Stitch – Extracted data (text and numbers for analysis)

This file contains concrete parameter names, numeric ranges, and check types pulled from the fetched Ink/Stitch docs. Use it as a single data reference for Cursor or an analyzer.

**Source docs:** All URLs listed in [docs/README.md](../../README.md) under `sources/inkstitch/`. Collected 2026-02-20.

**Code (Ink/Stitch):** Validation checks, param defaults, and how params are stored in SVG are extracted from the Ink/Stitch repository into [code-validation.md](code-validation.md). Use that file for: which errors/warnings the Troubleshoot extension reports; default values and effective minima (e.g. row_spacing_mm, max_stitch_length_mm); and SVG attribute names (`inkstitch:param_name`).

---

## 1. Stitch types and path declaration

| Param  | Path declaration              | Example stitch type |
|--------|-------------------------------|---------------------|
| Line   | Line with contour color       | Running Stitch      |
| Satin  | Two combined paths, optional rungs | Satin Column   |
| Fill   | Closed paths with fill color  | Fill Stitch         |

**Source:** params-overview.md → https://inkstitch.org/docs/params

---

## 2. Fill stitch – parameter names and facts

**Param names (Auto-Fill):**
- Automatically routed fill stitching, Fill method (AutoFill), Expand, Angle of lines of stitches, Gap Filling, Maximum fill stitch length, Spacing between rows, End row spacing, Stagger rows, Pull compensation, Pull compensation percent, Skip last stitch in each row, Underpath, Running stitch length, Running stitch tolerance, Randomize stitches, Random stitch length jitter, Random Seed, Minimum stitch length, Minimum jump stitch length, Allow lock stitches, Force lock stitches, Tack stitch, Lock stitch, Trim After, Stop After

**Underlay (fill):**
- Underlay (on/off), Fill angle (default 90° to top layer), Inset, Max stitch length, Row spacing (defaults to 3× top layer spacing), Skip last stitch in each row, Underpath

**Facts:**
- Underlay is enabled by default for fill. Row spacing for underlay defaults to 3× the spacing of the top layer. Fill angle for underlay defaults to 90° to top layer.
- Density is controlled by "Spacing between rows" (distance between rows of stitches, in mm).

**Source:** stitch-fill.md → https://inkstitch.org/docs/stitches/fill-stitch/

---

## 3. Satin column – parameter names and numeric guidance

**Underlay types (satin):**
- Center-walk underlay (running stitch down center): stitch length, tolerance, repeats, position (0%–100%)
- Contour underlay: stitch length, tolerance, inset distance (fixed), inset distance (proportional)
- Zig-zag underlay: inset (proportional/fixed), maximum stitch length, zig-zag spacing

**Satin top layer (examples):**
- Custom satin column, Method (Satin Column), Short stitch inset, Short stitch distance, Zig-Zag spacing, Pull compensation percentage, Pull compensation, Reverse rails, Swap rails, Stitch length, Tolerance, Start at nearest point, End at nearest point, Maximum stitch length, Minimum stitch length, etc.

**Source:** stitch-satin.md → https://inkstitch.org/docs/stitches/satin-column/

---

## 4. Underlay – numeric ranges (from tutorial)

| Underlay type    | Typical use (satin column width) | Numeric guidance                    |
|------------------|----------------------------------|-------------------------------------|
| Centerline       | 1 mm – 2 mm width                | Repeats: 2–3 for secure placement   |
| Contour          | 2 mm – 3.5 mm width (or wider with zig-zag) | Inset: 0.4 mm – 0.6 mm (varies by fabric) |
| Zig-zag          | With contour, satin wider than 4 mm | Set max stitch length for underlay  |
| Fill underlay    | Fill stitch                      | Wider row spacing, often perpendicular; can use multiple angles |

**Fabric/density rules (text):**
- thick fabric → more underlay; thin fabric → less underlay
- high stitch density → more underlay; low stitch density → less underlay

**Source:** tutorial-underlay.md → https://inkstitch.org/tutorials/underlay/

---

## 5. Running stitch – parameter names

**Param names:**
- Running stitch along paths, Method (Running stitch / Bean stitch), Repeats, Bean stitch number of repeats, Running stitch length, Running stitch tolerance, Randomize stitch length, Random stitch length jitter, Random Seed, Minimum stitch length, Minimum jump stitch length, Allow lock stitches, Force lock stitches, Tack stitch, Lock stitch, Trim After, Stop After

**Source:** stitch-running.md → https://inkstitch.org/docs/stitches/running-stitch/

---

## 6. Troubleshoot – what is checked

**Troubleshoot Objects:**
- Detects: errors (red), warnings (yellow), object type warnings
- Menu: Extensions > Ink/Stitch > Troubleshoot > Troubleshoot Objects
- If no selection: whole document is tested. One object can have multiple errors; fill shapes may show only the first error—run again to see more.

**Other tools:**
- Element Info: parameters and measurements of selected stitch elements
- Remove embroidery settings: options – remove print settings from SVG metadata; remove commands (all/none/specific); remove params
- Cleanup Document: remove small shapes, leftover objects; optional: delete empty groups/layers; configurable threshold
- Update Ink/Stitch SVG: manual update for elements from older files

**Source:** troubleshoot.md, tutorial-troubleshoot.md → https://inkstitch.org/docs/troubleshoot , https://inkstitch.org/tutorials/troubleshoot/

---

## 7. Push/pull compensation – factors (text data)

Factors that affect compensation amount:
- machine speed
- hoop / hooping
- underlay stitches
- stitch type, stitch length, stitch density
- design size
- stabilizer
- fabric

**Advice:** Test sew with same conditions as finished design; then adjust shapes. Compensate by overlapping areas or stitching one color on top of another.

**Source:** tutorial-pull-compensation.md → https://inkstitch.org/tutorials/push-pull-compensation/

---

## 8. Stitch path / routing – concepts (text data)

- Put elements in logical order (Re-stack elements in selected order).
- Avoid unnecessary jump stitches; do not rely only on trim to hide jumps.
- Jump to Stroke: creates running stitch from end of one element to start of next; can be hidden under other elements.
- Stroke: path direction defines start/end; even number of repeats = return to start.
- Satin: Start/End at nearest point (default); can use visual commands for start/end; rails should not be closed paths.
- Fill: start/end positions can be set with visual commands.

**Source:** tutorial-routing.md → https://inkstitch.org/tutorials/routing/

---

## 9. URL → local file mapping

| URL | Local file |
|-----|------------|
| https://inkstitch.org/docs/params | params-overview.md |
| https://inkstitch.org/docs/troubleshoot | troubleshoot.md |
| https://inkstitch.org/docs/stitches/fill-stitch/ | stitch-fill.md |
| https://inkstitch.org/docs/stitches/satin-column/ | stitch-satin.md |
| https://inkstitch.org/docs/stitch-library/ | stitch-library.md |
| https://inkstitch.org/docs/stitches/running-stitch/ | stitch-running.md |
| https://inkstitch.org/tutorials/underlay/ | tutorial-underlay.md |
| https://inkstitch.org/tutorials/troubleshoot/ | tutorial-troubleshoot.md |
| https://inkstitch.org/tutorials/push-pull-compensation/ | tutorial-pull-compensation.md |
| https://inkstitch.org/tutorials/routing/ | tutorial-routing.md |

---

*This extracted-data.md is generated from the content in the same folder. For full narrative and tables, open the corresponding source MD files.*
