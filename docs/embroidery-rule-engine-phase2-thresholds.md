# Phase 2 — Doc-derived thresholds (research)

Extracted from [rules/issue-checker-cross-reference.md](rules/issue-checker-cross-reference.md), [sources/inkstitch/extracted-data.md](sources/inkstitch/extracted-data.md), and [sources/inkstitch/code-validation.md](sources/inkstitch/code-validation.md). Vague cross-reference rows without numbers are listed as gaps.

## Threshold / condition table

| rule_id | category | condition | threshold | unit | source_file | confidence | notes |
|--------|----------|-----------|-----------|------|-------------|------------|-------|
| row_spacing_fill_low | parameters | row spacing below Ink/Stitch min | 0.15–0.2 typical min in validation | mm | code-validation.md | 0.9 | exact min varies by fill mode; engine uses 0.35 conservative from stitch-fill guidance |
| row_spacing_fill_high | parameters | row spacing too wide | vague (“visible gaps”) | mm | stitch-fill.md | 0.4 | engine uses 0.55 cap heuristic |
| satin_column_width_range | parameters | satin width | ~1.5–9 | mm | community fabric-presets / extracted-data | 0.75 | fabric-dependent |
| contour_underlay_inset | structure | underlay inset | 0.4–0.6 | mm | extracted-data.md §4 | 0.9 | |
| pull_compensation_start | parameters | starting pull comp stretchy | ~0.17–0.20 | mm | community-summary / failure-causes | 0.75 | fabric-dependent |
| geometry_node_count_warn | geometry | node_count high vs export hang | > 1000 | count | issue-checker-cross-reference.md §8; reddit-troubleshoot | 0.75 | |
| path_validation_errors | geometry | invalid / open path | boolean | none | code-validation.md | 0.9 | not all modeled in DesignReport yet |
| stitch_length_running | parameters | running stitch length | range in extracted-data | mm | extracted-data.md | 0.5 | engine defaults 1.5–6mm from generic practice |
| density_extreme | parameters | density / expand | vague vs fabric | ratio | stitch-fill.md; failure-causes | 0.5 | engine uses density_value > 0.6 heuristic |

## Cross-reference issue types without numeric source in this repo

- Ricoma: density / underlay / pull comp (no collected numeric articles per cross-reference).
- Wilcom / Hatch / Embird: many narrative-only fabric rows (use summaries for qualitative checks; bounds often “vague”).

## Engine coverage gap (explicit)

Rules that need richer `DesignReport` fields later: path direction, satin rail validation, narrow-fill regions, stabilizer flags, per-object pull comp on stretch without aggregate, exact machine format from workspace.
