# Ink/Stitch – Code-derived validation, defaults, and SVG params

Data extracted from the [inkstitch/inkstitch](https://github.com/inkstitch/inkstitch) repository for design analysis. Repo path used: `inkstitch/` (temporary clone, removed after fetch).

---

## 1. Validation / troubleshoot checks

The **Troubleshoot** extension (`lib/extensions/troubleshoot.py`) iterates over elements and collects:

- **Errors** (red): from `element.validation_errors()` – prevent the shape from being embroidered.
- **Warnings** (yellow): from `element.validation_warnings()` – subclass of `ValidationWarning`; Ink/Stitch will try to process the object.
- **Object type warnings** (orange): from `element.validation_warnings()` – subclass of `ObjectTypeWarning`; object may not work properly with Ink/Stitch.

Message types are defined in `lib/elements/validation.py`: `ValidationMessage` (base), `ValidationError`, `ValidationWarning`, `ObjectTypeWarning`. Each has `name`, `description`, `position`, `steps_to_solve`.

### Errors (by element type)

| Class | Element | Condition / meaning | File |
|-------|---------|---------------------|------|
| `NotStitchableError` | SatinColumn | No rails (`line_string_rails` empty) or `to_stitch_groups()` is empty | `lib/elements/satin_column.py` |
| `InvalidShapeError` | FillStitch | `shape.is_valid` is False (invalid polygon) | `lib/elements/fill_stitch.py` |

### Warnings (by element type)

**Satin column** (`lib/elements/satin_column.py`):

| Class | Name (approx) | Condition |
|-------|----------------|-----------|
| `ClosedPathWarning` | Rail is a closed path | Rail is closed |
| `DanglingRungWarning` | Rung doesn't intersect rails | Rung/rail intersection empty |
| `NoRungWarning` | Satin has no rungs | No rungs (when relevant) |
| `TooManyIntersectionsWarning` | Rungs intersect too many times | Intersection not a single point |
| `StrokeSatinWarning` | Simple Satin | Stroke-style satin |
| `NarrowSatinWarning` | Narrow Satin | Column very narrow |
| `TwoRungsWarning` | Satin has exactly two rungs | Exactly two rungs (ambiguous) |
| `UnequalPointsWarning` | Unequal number of points | Rails have different point counts |

**Fill stitch** (`lib/elements/fill_stitch.py`):

| Class | Name (approx) | Condition |
|-------|----------------|-----------|
| `SmallShapeWarning` | Small Fill | Shape area &lt; 20 (px²) |
| `ExpandWarning` | Expand | Expanded shape is empty |
| `UnderlayInsetWarning` | Inset | Shrunk shape for underlay inset is empty |
| `MissingGuideLineWarning` | Missing Guideline | Guided fill, no or empty guide line |
| `DisjointGuideLineWarning` | Disjointed Guide Line | Guide line disjoint from shape |
| `MultipleGuideLineWarning` | Multiple Guide Lines | More than one guide line |
| `UnconnectedWarning` | Unconnected | Invalid shape: hole outside shell |
| `BorderCrossWarning` | Border crosses itself | Invalid shape (other) |
| `StrokeAndFillWarning` | Fill and Stroke color | Stroke style set on fill |
| `NoGradientWarning` | No linear gradient color | Linear gradient fill but no gradient |
| `NoTartanStripeWarning` | No stripes to render | Tartan fill, no warp/weft stripes |
| `DefaultTartanStripeWarning` | No customized pattern | Tartan fill, no tartan node |

**Stroke** (`lib/elements/stroke.py`): `MultipleGuideLineWarning`, `TooNarrowSatinWarning`.

**Clone** (`lib/elements/clone.py`): `CloneWarning`.

### Object type warnings (not path / will be ignored unless marked)

| Class | Element | File |
|-------|---------|------|
| `TextTypeWarning` | Text | `lib/elements/text.py` |
| `ImageTypeWarning` | Image | `lib/elements/image.py` |
| `MarkerWarning` | Marker | `lib/elements/marker.py` |
| `EmptyD` | Empty path (d="") | `lib/elements/empty_d_object.py` |

---

## 2. Param defaults and limits (from code)

Defaults come from `@param(..., default=...)` on element properties and from `lib/update.py` for legacy. Code uses `max(..., 0.1 * PIXELS_PER_MM)` for some params to enforce a minimum. Values below are in user units (mm where applicable).

### Fill (FillStitch) – selected defaults

| Param | Default | File / note |
|-------|---------|-------------|
| `auto_fill` | True | fill_stitch.py |
| `row_spacing_mm` | 0.25 | fill_stitch.py; effective min 0.1 mm in code |
| `max_stitch_length_mm` | 3.0 | fill_stitch.py; effective min 0.1 mm |
| `angle` | 0 | fill_stitch.py |
| `expand_mm` | 0 | fill_stitch.py |
| `gap_fill_rows` | 0 | fill_stitch.py |
| `staggers` | 4 | fill_stitch.py |
| `skip_last` | False | fill_stitch.py |
| `fill_underlay` | True (docs); code uses param | fill_stitch.py |
| `fill_underlay_angle` | 90° (docs) | Underlay row spacing default 3× top in docs |

### Satin (SatinColumn) – selected defaults

| Param | Default | File / note |
|-------|---------|-------------|
| `center_walk_underlay_repeats` | 2 | satin_column.py, auto_satin.py |
| `center_walk_underlay_stitch_length_mm` | 3 | satin_column.py |
| `contour_underlay_stitch_length_mm` | 3 | satin_column.py |
| `contour_underlay_inset_mm` | 0.4 | satin_column.py |
| `zigzag_underlay_max_stitch_length_mm` | 4 (approx) | satin_column.py |

### Stroke / running

| Param | Default | File / note |
|-------|---------|-------------|
| `running_stitch_length_mm` | 1.5 | update.py (when migrating legacy) |
| `stroke_method` | running_stitch / manual_stitch (legacy) | update.py |

### Global / lock stitches

| Param | Default | File |
|-------|---------|------|
| `lock_start_scale_mm` | 0.7 | element.py |
| `lock_end_scale_mm` | 0.7 | element.py |
| `lock_start_scale_percent` | 100 | element.py |
| `lock_end_scale_percent` | 100 | element.py |

Limits: No single global min/max table; code clamps e.g. `max_stitch_length_mm` and `row_spacing_mm` to at least `0.1 * PIXELS_PER_MM`. For analyzer rules, use docs (e.g. underlay inset 0.4–0.6 mm) plus these defaults.

---

## 3. How params are stored in SVG

- **Namespace:** `http://inkstitch.org/namespace` (prefix `inkstitch`).
- **Attribute form:** `inkstitch:<param_name>`. Param names are stored as-is; the full attribute name is built with `inkex.addNS(param_name, 'inkstitch')` (see `lib/svg/tags.py`).
- **Read/write:** `element.get_param(param_name, default)` reads `node.get(INKSTITCH_ATTRIBS[param_name], "")`; `element.set_param(name, value)` does `node.set(INKSTITCH_ATTRIBS[name], str(value))` (in `lib/elements/element.py`).
- **Legacy:** Some old attributes were under a different prefix and are migrated in `lib/update.py` (e.g. `element.get_param('...', None)` and `set_param`).

### Param names (SVG attribute = `inkstitch:<name>`)

Full list is in `lib/svg/tags.py` in `inkstitch_attribs`. Selected params relevant to density, underlay, pull comp, stitch length:

- **Global / lock:** `min_stitch_length_mm`, `min_jump_stitch_length_mm`, `ties`, `force_lock_stitches`, `lock_start`, `lock_end`, `trim_after`, `stop_after`
- **Fill:** `angle`, `auto_fill`, `fill_method`, `expand_mm`, `fill_underlay`, `fill_underlay_angle`, `fill_underlay_inset_mm`, `fill_underlay_max_stitch_length_mm`, `fill_underlay_row_spacing_mm`, `max_stitch_length_mm`, `row_spacing_mm`, `end_row_spacing_mm`, `skip_last`, `staggers`, `underpath`, `gap_fill_rows`
- **Stroke:** `stroke_method`, `bean_stitch_repeats`, `repeats`, `running_stitch_length_mm`, `running_stitch_tolerance_mm`
- **Satin:** `satin_column`, `satin_method`, `short_stitch_distance_mm`, `short_stitch_inset`, `reverse_rails`, `swap_satin_rails`, `center_walk_underlay`, `center_walk_underlay_stitch_length_mm`, `center_walk_underlay_repeats`, `center_walk_underlay_position`, `contour_underlay`, `contour_underlay_inset_mm`, `contour_underlay_inset_percent`, `zigzag_underlay`, `zigzag_underlay_max_stitch_length_mm`, `pull_compensation_mm`, `pull_compensation_percent`, `start_at_nearest_point`, `end_at_nearest_point`

So in SVG you will see e.g. `inkstitch:row_spacing_mm`, `inkstitch:fill_underlay`, `inkstitch:pull_compensation_mm`.

---

*Extracted from inkstitch repo. For narrative and best practices, see the other files in this folder (troubleshoot.md, stitch-fill.md, tutorial-underlay.md, etc.).*
