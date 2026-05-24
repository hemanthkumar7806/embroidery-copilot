# Embroidery design analysis – documentation index

This folder is the single place for collected embroidery documentation. It is used to analyze embroidery designs and point out issues (e.g. density, underlay, pull compensation, path errors, stitch order).

## Structure

- **sources/** – Raw or summarized content by source (Ink/Stitch, Wilcom, community, etc.).
- **rules/** – [issue-checker-cross-reference.md](rules/issue-checker-cross-reference.md): what to check per issue type, which source files to use (Ink/Stitch, Wilcom, Hatch, Embird, Ricoma), and gaps to add.
- [glossary.md](glossary.md) – Shared terms (density, underlay, pull comp, satin, fill, etc.).

## Issue type → where it’s documented

| Issue type | Source files (Ink/Stitch) | Source files (Wilcom) | Source files (Hatch) | Source files (Embird) | Source files (Ricoma) | Source files (Community) |
|------------|---------------------------|------------------------|------------------------|------------------------|------------------------|---------------------------|
| **Density** | stitch-fill.md, stitch-satin.md, stitch-running.md, tutorial-underlay.md, extracted-data.md | manage-fabrics.md, underlay-pull-compensation.md | adjust-stitch-densities.md, manage-fabrics.md | parameters-whole-design.md, parameters-fill.md, parameters-column.md | — | fabric-presets.md, common-mistakes.md, community-summary.md |
| **Underlay** | stitch-fill.md, stitch-satin.md, tutorial-underlay.md, extracted-data.md | underlay-pull-compensation.md, stabilizing-automatic-underlay.md, underlay-types.md | automatic-underlay.md, manage-fabrics.md | parameters-fill.md, parameters-column.md, parameters-whole-design.md, digitizing-get-started.md | — | fabric-presets.md, failure-causes.md |
| **Pull compensation** | stitch-fill.md, stitch-satin.md, tutorial-pull-compensation.md, extracted-data.md | underlay-pull-compensation.md, compensating-fabric-stretch.md | pull-compensation.md, choose-auto-fabrics.md | parameters-whole-design.md, parameters-fill.md, parameters-column.md, digitizing-get-started.md | — | fabric-presets.md, failure-causes.md, community-summary.md |
| **Path errors / troubleshoot** | troubleshoot.md, tutorial-troubleshoot.md, extracted-data.md, code-validation.md | — | — | — | — | common-mistakes.md, failure-causes.md |
| **Stitch order / routing** | tutorial-routing.md, extracted-data.md | — | — | digitizing-get-started.md | — | common-mistakes.md, failure-causes.md |
| **Stitch types & params** | params-overview.md, stitch-library.md, stitch-fill.md, stitch-satin.md, stitch-running.md, extracted-data.md, code-validation.md | manage-fabrics.md | manage-fabrics.md, choose-auto-fabrics.md | parameters-overview.md, parameters-fill.md, parameters-column.md | chroma-supported-file-types.md | fabric-presets.md (satin width), failure-causes.md |

## Sources: Ink/Stitch (`sources/inkstitch/`)

**Data reference (for Cursor / analyzers):** [extracted-data.md](sources/inkstitch/extracted-data.md) – parameter names, numeric ranges (e.g. underlay inset 0.4–0.6 mm, satin width ranges), troubleshoot check types, and URL→file mapping in one place.

| File | Description |
|------|-------------|
| [params-overview.md](sources/inkstitch/params-overview.md) | Params dialog overview; stitch types (line, satin, fill); presets and simulator. |
| [troubleshoot.md](sources/inkstitch/troubleshoot.md) | Troubleshoot extension: Troubleshoot Objects, Element Info, Remove settings, Cleanup Document, Update SVG. |
| [stitch-fill.md](sources/inkstitch/stitch-fill.md) | Fill stitch: Auto-Fill and Legacy Fill params, underlay, pull compensation, row spacing. |
| [stitch-satin.md](sources/inkstitch/stitch-satin.md) | Satin column: creation methods, params, center-walk/contour/zig-zag underlay. |
| [stitch-library.md](sources/inkstitch/stitch-library.md) | Index of all stitch types (stroke, satin, fill) with links to detailed pages. |
| [stitch-running.md](sources/inkstitch/stitch-running.md) | Running stitch params: length, tolerance, repeats, bean stitch, routing. |
| [tutorial-underlay.md](sources/inkstitch/tutorial-underlay.md) | Why underlay matters; types (centerline, contour, zig-zag, fill, manual); fabric and density. |
| [tutorial-troubleshoot.md](sources/inkstitch/tutorial-troubleshoot.md) | Troubleshooting workflow: identify element, use tools, check params, test, embroider. |
| [tutorial-pull-compensation.md](sources/inkstitch/tutorial-pull-compensation.md) | Push/pull effect and how to compensate (overlap, test-sew). |
| [tutorial-routing.md](sources/inkstitch/tutorial-routing.md) | Stitch path optimization: order, jump stitches, stroke/satin/fill routing options. |
| [extracted-data.md](sources/inkstitch/extracted-data.md) | **Data only:** param names, numbers (density/underlay/pull comp), check types, URL→file map. |
| [code-validation.md](sources/inkstitch/code-validation.md) | **From Ink/Stitch code:** validation/troubleshoot checks (errors, warnings), param defaults/limits, SVG param storage (`inkstitch:*`). |

## Sources: Wilcom (`sources/wilcom/`)

| File | Description |
|------|-------------|
| [underlay-pull-compensation.md](sources/wilcom/underlay-pull-compensation.md) | Underlay & pull comp overview; stitch spacing, pull comp, underlay for object/fabric. |
| [stabilizing-automatic-underlay.md](sources/wilcom/stabilizing-automatic-underlay.md) | Why underlay; automatic underlay; loft, stabilizer. |
| [underlay-types.md](sources/wilcom/underlay-types.md) | Underlay types; default values from Auto Fabric, presets, or templates. |
| [compensating-fabric-stretch.md](sources/wilcom/compensating-fabric-stretch.md) | Pull compensation (fabric stretch); overstitching; Object Properties. |
| [manage-fabrics.md](sources/wilcom/manage-fabrics.md) | Fabric presets; Tatami/Wide Satin/Narrow Satin/Lettering; density slider; length/spacing. |
| [wilcom-summary.md](sources/wilcom/wilcom-summary.md) | **Data only:** object groups, underlay/pull comp/density by type, stabilizer; for analyzers. |

## Sources: Hatch (`sources/hatch/`)

| File | Description |
|------|-------------|
| [automatic-underlay.md](sources/hatch/automatic-underlay.md) | Underlay toggle; Center Run, Edge Run, Zigzag, Tatami; dual underlays; fabric. |
| [pull-compensation.md](sources/hatch/pull-compensation.md) | Pull comp; overstitching; Auto Fabric; Object Properties; backing/topping. |
| [adjust-stitch-densities.md](sources/hatch/adjust-stitch-densities.md) | Adjust Stitch Spacing; percentage density override; fabric/thread. |
| [manage-fabrics.md](sources/hatch/manage-fabrics.md) | Custom fabrics; Tatami/Embossed Fill, Wide Satin, Narrow Satin, Lettering; stabilizers. |
| [choose-auto-fabrics.md](sources/hatch/choose-auto-fabrics.md) | Auto Fabric dialog; pull comp; recommended stabilizers; backing types. |
| [hatch-summary.md](sources/hatch/hatch-summary.md) | **Data only:** object groups, underlay types (Center Run, Edge Run, Zigzag, Tatami), density, Auto Fabric, stabilizer; for analyzers. |

## Sources: Embird (`sources/embird/`)

| File | Description |
|------|-------------|
| [parameters-overview.md](sources/embird/parameters-overview.md) | Parameters overview; tabs (Whole Design, Fill, Column, etc.); default params. |
| [parameters-whole-design.md](sources/embird/parameters-whole-design.md) | Additional Density, Additional Pull Compensation; underlay offset (Edge, Zig-Zag) global. |
| [parameters-fill.md](sources/embird/parameters-fill.md) | Fill: density, pull compensation; Edge/Zig-Zag underlays; Plain Fill, Motifs, Auto Column. |
| [parameters-column.md](sources/embird/parameters-column.md) | Column: density, pull compensation; Center/Edge/Zig-Zag underlay; Auto Select Underlay. |
| [digitizing-get-started.md](sources/embird/digitizing-get-started.md) | Overlap, underlay rules, pull comp, stitch order, connections; density 0.1 mm grid. |
| [embird-summary.md](sources/embird/embird-summary.md) | **Data only:** object types (Fill, Column), underlay (Center, Edge, Zig-Zag), density, pull comp, global offset; for analyzers. |

## Sources: Ricoma (`sources/ricoma/`)

| File | Description |
|------|-------------|
| [chroma-supported-file-types.md](sources/ricoma/chroma-supported-file-types.md) | Chroma supported file types (import/export chart). |
| [chroma-activation-limit-reached.md](sources/ricoma/chroma-activation-limit-reached.md) | Activation limit; deactivate on one device to activate on another. |
| [chroma-send-design-files-to-machine.md](sources/ricoma/chroma-send-design-files-to-machine.md) | Troubleshooting wired/wireless transfer from Chroma to machine. |
| [chroma-download-install.md](sources/ricoma/chroma-download-install.md) | Download and install Chroma (stub; fetch timed out). |
| [ricoma-summary.md](sources/ricoma/ricoma-summary.md) | **Data only:** coverage note (limited digitizing docs), URL→file map, failed fetches; for analyzers. |

## Sources: Community (`sources/community/`)

Content curated from blogs (e.g. DigitizingUSA, The Embroidery Cloud, Hooping Station), forums (t-shirtforums, Reddit r/Machine_Embroidery), and YouTube, with attribution. Only concrete numbers and clear failure causes are included. Used to supplement official docs on density-by-fabric and real-world failure causes.

| File | Description |
|------|-------------|
| [common-mistakes.md](sources/community/common-mistakes.md) | Common mistakes: density, underlay, pathing, stitch type, test runs, fabric; with numbers and source links. |
| [fabric-presets.md](sources/community/fabric-presets.md) | Fabric-specific tips for **all cloth types**: cotton, fleece, denim, leather, silk, satin, knits (e.g. hoodie), terry/towel, twill, canvas, drill, pique, vinyl, sherpa, cap, plush; density (mm), underlay, pull comp. |
| [failure-causes.md](sources/community/failure-causes.md) | Why designs fail: too dense, no underlay, wrong pull comp, bad pathing, wrong stitch type, fabric, stabilizer/hooping. |
| [community-summary.md](sources/community/community-summary.md) | **Data only:** numeric rules, failure-cause list, fabric→presets (all cloth types), URL→file mapping; for analyzers. |
| [youtube-dataset.md](sources/community/youtube-dataset.md) | YouTube transcript dataset: how to fetch transcript via Transcript API (curl), where to paste extracted content. |

## Usage

Content here is intended for RAG or AI context when building an automated design analyzer that reads designs (e.g. SVG/EMB) and reports issues against these sources. When developing the issue checker, use **[rules/issue-checker-cross-reference.md](rules/issue-checker-cross-reference.md)** to cross-check: for each issue type it lists what to verify, which Ink/Stitch, Wilcom, Hatch, Embird, and Ricoma files apply, and what is missing or single-source so you can add checks as needed.

All fetches for the initial Ink/Stitch set (10 URLs) completed successfully. Wilcom set (5 URLs), Hatch set (5 URLs), and Embird set (5 URLs) completed successfully. Ricoma set (4 URLs): 3 fetched, 1 timed out (chroma-download-install); see [ricoma-summary.md](sources/ricoma/ricoma-summary.md).
