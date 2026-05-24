# Issue checker cross-reference

Use this when building or extending an embroidery design issue checker. For each issue type it lists **what to check**, **where it’s documented** (Ink/Stitch, Wilcom, Hatch, Embird, Ricoma, Community), and **gaps** (missing checks or single-source coverage). **Community** supplements density-by-fabric and real-world failure causes (see [sources/community/](../sources/community/)).

---

## 1. Density

| What to check | Ink/Stitch | Wilcom | Hatch | Embird | Ricoma | Community |
|---------------|------------|--------|-------|--------|--------|------------|
| Row spacing / spacing between rows (fill) in reasonable range | [stitch-fill.md](../sources/inkstitch/stitch-fill.md), [extracted-data.md](../sources/inkstitch/extracted-data.md), [code-validation.md](../sources/inkstitch/code-validation.md) | [manage-fabrics.md](../sources/wilcom/manage-fabrics.md), [underlay-pull-compensation.md](../sources/wilcom/underlay-pull-compensation.md) | [adjust-stitch-densities.md](../sources/hatch/adjust-stitch-densities.md), [manage-fabrics.md](../sources/hatch/manage-fabrics.md) | [parameters-fill.md](../sources/embird/parameters-fill.md), [parameters-column.md](../sources/embird/parameters-column.md), [parameters-whole-design.md](../sources/embird/parameters-whole-design.md) | — | [fabric-presets.md](../sources/community/fabric-presets.md), [community-summary.md](../sources/community/community-summary.md) §1 |
| Density appropriate for fabric (high density → more underlay) | [tutorial-underlay.md](../sources/inkstitch/tutorial-underlay.md), extracted-data §4 | [manage-fabrics.md](../sources/wilcom/manage-fabrics.md) – fabric presets per object group | [manage-fabrics.md](../sources/hatch/manage-fabrics.md), [choose-auto-fabrics.md](../sources/hatch/choose-auto-fabrics.md) | [digitizing-get-started.md](../sources/embird/digitizing-get-started.md), [parameters-whole-design.md](../sources/embird/parameters-whole-design.md) – Additional Density | — | [fabric-presets.md](../sources/community/fabric-presets.md) §3 |
| Satin: density / column width (Wide vs Narrow Satin) | [stitch-satin.md](../sources/inkstitch/stitch-satin.md), extracted-data §3 | [manage-fabrics.md](../sources/wilcom/manage-fabrics.md) – density slider for satin | [manage-fabrics.md](../sources/hatch/manage-fabrics.md) – Wide/Narrow Satin | [parameters-column.md](../sources/embird/parameters-column.md) | — | [fabric-presets.md](../sources/community/fabric-presets.md) – satin 1.5–9 mm |
| Min/max numeric limits (e.g. row_spacing_mm) | [code-validation.md](../sources/inkstitch/code-validation.md) | — (no code-derived limits; use docs) | — | — | — | [community-summary.md](../sources/community/community-summary.md) §1 |
| **Density by fabric (hoodie, cap, fleece)** | — | — | — | — | — | [fabric-presets.md](../sources/community/fabric-presets.md), [community-summary.md](../sources/community/community-summary.md) §3 |

**Gaps:** Wilcom, Hatch, and Embird have no explicit numeric bounds; Ricoma: no density docs in collected articles. Use fabric presets as reference. **Community** supplies density-by-fabric numbers (hoodie, cap, fleece, etc.). Consider adding: “density too high for object size” (puckering risk).

---

## 2. Underlay

| What to check | Ink/Stitch | Wilcom | Hatch | Embird | Ricoma | Community |
|---------------|------------|--------|-------|--------|--------|------------|
| Underlay present where needed (fill, satin) | [stitch-fill.md](../sources/inkstitch/stitch-fill.md), [tutorial-underlay.md](../sources/inkstitch/tutorial-underlay.md) | [stabilizing-automatic-underlay.md](../sources/wilcom/stabilizing-automatic-underlay.md), [underlay-pull-compensation.md](../sources/wilcom/underlay-pull-compensation.md) | [automatic-underlay.md](../sources/hatch/automatic-underlay.md), [manage-fabrics.md](../sources/hatch/manage-fabrics.md) | [parameters-fill.md](../sources/embird/parameters-fill.md), [parameters-column.md](../sources/embird/parameters-column.md), [digitizing-get-started.md](../sources/embird/digitizing-get-started.md) | — | [common-mistakes.md](../sources/community/common-mistakes.md), [failure-causes.md](../sources/community/failure-causes.md) |
| Type matches object (centerline vs contour vs zig-zag vs fill) | [stitch-satin.md](../sources/inkstitch/stitch-satin.md), [extracted-data.md](../sources/inkstitch/extracted-data.md) §4 | [underlay-types.md](../sources/wilcom/underlay-types.md), [manage-fabrics.md](../sources/wilcom/manage-fabrics.md) – by Tatami/Satin/Lettering | [automatic-underlay.md](../sources/hatch/automatic-underlay.md) – Center Run, Edge Run, Zigzag, Tatami | [parameters-fill.md](../sources/embird/parameters-fill.md), [parameters-column.md](../sources/embird/parameters-column.md) – Center, Edge, Zig-Zag | — | [fabric-presets.md](../sources/community/fabric-presets.md) – underlay by fabric/size |
| Inset / row spacing for underlay (e.g. contour 0.4–0.6 mm) | [extracted-data.md](../sources/inkstitch/extracted-data.md) §4, [code-validation.md](../sources/inkstitch/code-validation.md) | [underlay-types.md](../sources/wilcom/underlay-types.md) – defaults from Auto Fabric/presets/templates | [automatic-underlay.md](../sources/hatch/automatic-underlay.md) – defaults from auto fabric/template | [parameters-whole-design.md](../sources/embird/parameters-whole-design.md) – Offset tab | — | — |
| Larger areas / stretchy fabric need more underlay | [tutorial-underlay.md](../sources/inkstitch/tutorial-underlay.md) | [underlay-types.md](../sources/wilcom/underlay-types.md), [stabilizing-automatic-underlay.md](../sources/wilcom/stabilizing-automatic-underlay.md) | [automatic-underlay.md](../sources/hatch/automatic-underlay.md) | [digitizing-get-started.md](../sources/embird/digitizing-get-started.md) | — | [fabric-presets.md](../sources/community/fabric-presets.md) – stretchy: Zigzag+Edge |

**Gaps:** None major; Ink/Stitch, Wilcom, Hatch, Embird align. Ricoma: no underlay docs in collected articles. **Community** adds underlay-by-fabric (stretchy, narrow satin). Optional: underlay margins (Wilcom has a doc we didn’t fetch).

---

## 3. Pull compensation

| What to check | Ink/Stitch | Wilcom | Hatch | Embird | Ricoma | Community |
|---------------|------------|--------|-------|--------|--------|------------|
| Pull comp set for stretchy fabric / large areas | [tutorial-pull-compensation.md](../sources/inkstitch/tutorial-pull-compensation.md), [extracted-data.md](../sources/inkstitch/extracted-data.md) §7 | [compensating-fabric-stretch.md](../sources/wilcom/compensating-fabric-stretch.md), [underlay-pull-compensation.md](../sources/wilcom/underlay-pull-compensation.md) | [pull-compensation.md](../sources/hatch/pull-compensation.md), [choose-auto-fabrics.md](../sources/hatch/choose-auto-fabrics.md) | [parameters-whole-design.md](../sources/embird/parameters-whole-design.md), [parameters-fill.md](../sources/embird/parameters-fill.md), [parameters-column.md](../sources/embird/parameters-column.md), [digitizing-get-started.md](../sources/embird/digitizing-get-started.md) | — | [fabric-presets.md](../sources/community/fabric-presets.md), [failure-causes.md](../sources/community/failure-causes.md) – ~0.17–0.20 mm start |
| Overstitching / overlap vs fixed/percent params | [stitch-fill.md](../sources/inkstitch/stitch-fill.md), [stitch-satin.md](../sources/inkstitch/stitch-satin.md) | [compensating-fabric-stretch.md](../sources/wilcom/compensating-fabric-stretch.md) – Object Properties docker | [pull-compensation.md](../sources/hatch/pull-compensation.md) – Object Properties | [parameters-fill.md](../sources/embird/parameters-fill.md), [parameters-column.md](../sources/embird/parameters-column.md) – Pull Compensation; [parameters-whole-design.md](../sources/embird/parameters-whole-design.md) – Additional Pull Compensation | — | [fabric-presets.md](../sources/community/fabric-presets.md) – overlap rule |
| Factors: underlay, backing, topping, stabilizer, fabric | [tutorial-pull-compensation.md](../sources/inkstitch/tutorial-pull-compensation.md) | [compensating-fabric-stretch.md](../sources/wilcom/compensating-fabric-stretch.md) – backing/topping tip | [pull-compensation.md](../sources/hatch/pull-compensation.md), [choose-auto-fabrics.md](../sources/hatch/choose-auto-fabrics.md) | [digitizing-get-started.md](../sources/embird/digitizing-get-started.md) | — | [failure-causes.md](../sources/community/failure-causes.md) |

**Gaps:** None. Ricoma: no pull comp docs in collected articles. **Community** adds real-world pull-comp failure causes and starting values. Consider adding a check: “stretchy fabric but no pull compensation” (warning).

---

## 4. Path errors / troubleshoot

| What to check | Ink/Stitch | Wilcom | Hatch | Embird | Ricoma | Community |
|---------------|------------|--------|-------|--------|--------|------------|
| Invalid path / wrong path direction / crossing borders | [troubleshoot.md](../sources/inkstitch/troubleshoot.md), [tutorial-troubleshoot.md](../sources/inkstitch/tutorial-troubleshoot.md), [code-validation.md](../sources/inkstitch/code-validation.md) | — | — | — | — | [failure-causes.md](../sources/community/failure-causes.md) – bad pathing |
| Too-small shape, empty expand, underlay inset empty | [code-validation.md](../sources/inkstitch/code-validation.md) – Fill warnings | — | — | — | — | — |
| Satin: closed rail, dangling rung, unequal points, etc. | [code-validation.md](../sources/inkstitch/code-validation.md) – Satin warnings | — | — | — | — | — |
| Cleanup: tiny shapes, leftover objects | [troubleshoot.md](../sources/inkstitch/troubleshoot.md), [extracted-data.md](../sources/inkstitch/extracted-data.md) §6 | — | — | — | — | — |

**Gaps:** Path/validation checks exist **only in Ink/Stitch** (Troubleshoot + code). **Community** adds pathing as a failure cause. For EMB/Wilcom/Hatch/Embird/Ricoma-native designs, add rules from those docs or tooling when available; for now treat as Ink/Stitch-only.

---

## 5. Stitch order / routing

| What to check | Ink/Stitch | Wilcom | Hatch | Embird | Ricoma | Community |
|---------------|------------|--------|-------|--------|--------|------------|
| Element order (re-stack, start/end commands) | [tutorial-routing.md](../sources/inkstitch/tutorial-routing.md), [extracted-data.md](../sources/inkstitch/extracted-data.md) §8 | — | — | [digitizing-get-started.md](../sources/embird/digitizing-get-started.md) – object order, connections | — | [common-mistakes.md](../sources/community/common-mistakes.md), [failure-causes.md](../sources/community/failure-causes.md) |
| Jump stitches: minimize; jump-to-stroke where useful | [tutorial-routing.md](../sources/inkstitch/tutorial-routing.md) | — | — | [digitizing-get-started.md](../sources/embird/digitizing-get-started.md) | — | [common-mistakes.md](../sources/community/common-mistakes.md) |
| Satin: start/end at nearest point; fill start/end | [extracted-data.md](../sources/inkstitch/extracted-data.md) §8 | — | — | — | — | — |

**Gaps:** Routing/order is **only in Ink/Stitch** in our set. **Community** adds pathing/jump as common mistake and failure cause. Ricoma: no routing docs in collected articles. Consider fetching Wilcom “routing” or “stitch order” docs later if needed.

---

## 6. Stitch types & params

| What to check | Ink/Stitch | Wilcom | Hatch | Embird | Ricoma | Community |
|---------------|------------|--------|-------|--------|--------|------------|
| Param names, defaults, SVG storage | [params-overview.md](../sources/inkstitch/params-overview.md), [code-validation.md](../sources/inkstitch/code-validation.md), [extracted-data.md](../sources/inkstitch/extracted-data.md) | [manage-fabrics.md](../sources/wilcom/manage-fabrics.md), [wilcom-summary.md](../sources/wilcom/wilcom-summary.md) | [manage-fabrics.md](../sources/hatch/manage-fabrics.md), [hatch-summary.md](../sources/hatch/hatch-summary.md) | [parameters-overview.md](../sources/embird/parameters-overview.md), [parameters-fill.md](../sources/embird/parameters-fill.md), [parameters-column.md](../sources/embird/parameters-column.md), [embird-summary.md](../sources/embird/embird-summary.md) | [chroma-supported-file-types.md](../sources/ricoma/chroma-supported-file-types.md), [ricoma-summary.md](../sources/ricoma/ricoma-summary.md) | [community-summary.md](../sources/community/community-summary.md) §1 |
| Object groups: Fill vs Satin vs Lettering (Wilcom/Hatch: Tatami, Wide/Narrow Satin, Lettering) | [params-overview.md](../sources/inkstitch/params-overview.md), [stitch-library.md](../sources/inkstitch/stitch-library.md) | [manage-fabrics.md](../sources/wilcom/manage-fabrics.md) | [manage-fabrics.md](../sources/hatch/manage-fabrics.md) – Tatami/Embossed Fill, Wide/Narrow Satin, Lettering | [parameters-overview.md](../sources/embird/parameters-overview.md) – Fill, Column, Outline, etc. | — | [fabric-presets.md](../sources/community/fabric-presets.md) – satin width; [common-mistakes.md](../sources/community/common-mistakes.md) – stitch type |

**Gaps:** None. Wilcom, Hatch, and Embird add fabric/object-group defaults; Ricoma has file types only. **Community** adds satin width limits and wrong-stitch-type as failure cause. Use [wilcom-summary.md](../sources/wilcom/wilcom-summary.md), [hatch-summary.md](../sources/hatch/hatch-summary.md), [embird-summary.md](../sources/embird/embird-summary.md), and [ricoma-summary.md](../sources/ricoma/ricoma-summary.md) for single data references.

---

## 7. Optional / cross-cutting

| What to check | Ink/Stitch | Wilcom | Hatch | Embird | Ricoma | Community |
|---------------|------------|--------|-------|--------|--------|------------|
| Stabilizer / backing / topping recommended for fabric | — (mentioned in passing) | [manage-fabrics.md](../sources/wilcom/manage-fabrics.md) – stabilizer tab, [compensating-fabric-stretch.md](../sources/wilcom/compensating-fabric-stretch.md) | [choose-auto-fabrics.md](../sources/hatch/choose-auto-fabrics.md), [manage-fabrics.md](../sources/hatch/manage-fabrics.md) | — | — | [failure-causes.md](../sources/community/failure-causes.md) – stabilizer/hooping |
| Test-sew / real conditions for pull comp and density | [tutorial-pull-compensation.md](../sources/inkstitch/tutorial-pull-compensation.md), [tutorial-troubleshoot.md](../sources/inkstitch/tutorial-troubleshoot.md) | [compensating-fabric-stretch.md](../sources/wilcom/compensating-fabric-stretch.md) | [pull-compensation.md](../sources/hatch/pull-compensation.md) | [digitizing-get-started.md](../sources/embird/digitizing-get-started.md) | — | [common-mistakes.md](../sources/community/common-mistakes.md) – no test runs |
| **Real-world failure causes (why design failed)** | — | — | — | — | — | [failure-causes.md](../sources/community/failure-causes.md), [community-summary.md](../sources/community/community-summary.md) §2 |

**Gaps:** Stabilizer/backing/topping is explicit in Wilcom and Hatch (not in Embird or Ricoma docs we collected). **Community** adds stabilizer/hooping as failure cause. Could add a soft check or hint (“consider stabilizer for this fabric”) if fabric type is known.

---

## 8. Geometry / stitch-generation feasibility

| What to check | Ink/Stitch | Wilcom | Hatch | Embird | Ricoma | Community |
|---------------|------------|--------|-------|--------|--------|------------|
| Excessive nodes / unoptimized path geometry | [code-validation.md](../sources/inkstitch/code-validation.md) (Fill warnings) | — | — | — | — | [reddit-troubleshoot-passes-no-stitch-out.md](../sources/community/reddit-troubleshoot-passes-no-stitch-out.md) |
| Narrow fill pathing (fill in regions too narrow for stitch rows) | — | — | — | — | — | [reddit-troubleshoot-passes-no-stitch-out.md](../sources/community/reddit-troubleshoot-passes-no-stitch-out.md) |
| Troubleshoot passes but stitch plan / export hangs or is very slow | — | — | — | — | — | [reddit-troubleshoot-passes-no-stitch-out.md](../sources/community/reddit-troubleshoot-passes-no-stitch-out.md) |
| Overuse of fill (everything as fill when satin/run would be better) | [stitch-library.md](../sources/inkstitch/stitch-library.md), [params-overview.md](../sources/inkstitch/params-overview.md) | — | — | — | — | [reddit-troubleshoot-passes-no-stitch-out.md](../sources/community/reddit-troubleshoot-passes-no-stitch-out.md), [common-mistakes.md](../sources/community/common-mistakes.md) |

**Gaps:** These checks are not covered by Ink/Stitch Troubleshoot (design can pass and still freeze on export). Use `get_design_report` with `include_geometry=true` to get `node_count` / `segment_count`; warn if node_count &gt; 1000. See [reddit-troubleshoot-passes-no-stitch-out.md](../sources/community/reddit-troubleshoot-passes-no-stitch-out.md) for mapping and suggested fixes.

---

## Summary: coverage and missing checks

| Issue type | Ink/Stitch | Wilcom | Hatch | Embird | Ricoma | Community | Consider adding |
|------------|------------|--------|-------|--------|--------|-----------|------------------|
| Density | ✓ | ✓ | ✓ | ✓ | — | ✓ (fabric presets, numbers) | density vs object size; numeric limits only in Ink/Stitch |
| Underlay | ✓ | ✓ | ✓ | ✓ | — | ✓ (by fabric/size) | underlay margins (fetch from Wilcom?) |
| Pull compensation | ✓ | ✓ | ✓ | ✓ | — | ✓ (failure causes, 0.17–0.20 mm) | “stretchy fabric, no pull comp” |
| Path errors | ✓ (full) | — | — | — | — | ✓ (failure cause) | Wilcom/Hatch/Embird/Ricoma validation when available |
| Stitch order / routing | ✓ | — | — | ✓ (partial) | — | ✓ (mistakes, failure cause) | Wilcom/Hatch routing docs (fetch?) |
| Stitch types & params | ✓ | ✓ | ✓ | ✓ | partial (file types) | ✓ (satin width, wrong type) | — |
| Stabilizer/backing | — | ✓ | ✓ | — | — | ✓ (failure cause) | optional hint by fabric |
| **Density by fabric (hoodie, cap, etc.)** | — | — | — | — | — | ✓ only | [fabric-presets.md](../sources/community/fabric-presets.md), [community-summary.md](../sources/community/community-summary.md) |
| **Real-world failure causes** | — | — | — | — | — | ✓ only | [failure-causes.md](../sources/community/failure-causes.md), [community-summary.md](../sources/community/community-summary.md) §2 |
| **Geometry / stitch-generation feasibility** | partial (code-validation) | — | — | — | — | ✓ only | [reddit-troubleshoot-passes-no-stitch-out.md](../sources/community/reddit-troubleshoot-passes-no-stitch-out.md); use get_design_report include_geometry, warn if node_count &gt; 1000 |

When you add a new check to the issue checker, consult the row for that issue type above and the linked source files so you don’t miss the other source’s rules. **Community** sources supplement official docs for density-by-fabric and “why design failed” checks. For “Troubleshoot passes but export hangs,” see [reddit-troubleshoot-passes-no-stitch-out.md](../sources/community/reddit-troubleshoot-passes-no-stitch-out.md).
