# Glossary – embroidery design analysis

Shared terms for docs and analyzer rules. Use these consistently when analyzing designs or writing rules.

---

## Stitch types and structures

- **Line (stroke)** – Stitches along a path (contour). Example: running stitch, bean stitch. Path declaration: line with contour color.
- **Satin** – Zigzag stitches between two boundary lines (rails). Used for borders, letters, small fills. Column width = distance between rails. Path declaration: two combined paths, optional rungs.
- **Fill** – Rows of stitches covering a closed shape. Path declaration: closed path with fill color. Includes Auto-Fill, contour fill, meander, circular fill, etc.
- **Running stitch** – Small stitches following a path; length and repeats are the main params.
- **Underlay** – One or more layers of stitches sewn before the top (cover) layer to stabilize fabric, define edges, and support the top stitches.

---

## Density

- **Density** – How closely stitches are spaced. For fill: controlled by **spacing between rows** (distance between rows, in mm). Tighter spacing = higher density. High density often needs more underlay; very high density can cause puckering or registration issues.
- **Row spacing** – Distance between rows of stitches (fill or underlay). In Ink/Stitch params: “Spacing between rows” (fill), “Row spacing” (underlay). Underlay row spacing often defaults to 3× top layer for fill.

---

## Underlay types

- **Centerline (center-walk)** – Running stitch down the center of a satin column. Typical for satin 1–2 mm wide; sometimes 2–3 repeats.
- **Contour** – Running stitch along the outline of the object, inset from the edge. Typical for satin 2–3.5 mm; inset often 0.4–0.6 mm (fabric-dependent).
- **Zig-zag underlay** – Lower-density satin sewn under the main satin. Used with contour for satin wider than ~4 mm. Set max stitch length to avoid destabilizing.
- **Fill underlay** – Fill stitch with wider row spacing, usually perpendicular (e.g. 90°) to top fill. Default in Ink/Stitch for fill; can use multiple angles.
- **Manual underlay** – Running stitches added by the digitizer (e.g. at 90° satin meets, under 3D foam, or to stabilize before fills).

---

## Pull compensation (push/pull)

- **Pull** – Fabric drawn inward along stitch direction as the machine sews.
- **Push** – Fabric pushed outward, e.g. where dense stitches pack and spread edges.
- **Pull compensation** – Params that expand stitches or rows outward so the sewn result matches the intended size/shape. In Ink/Stitch: “Pull compensation” (fixed length), “Pull compensation percent” (percentage of width). Factors that affect how much to use: machine speed, hooping, underlay, stitch type/length/density, design size, stabilizer, fabric.

---

## Path and routing

- **Path direction** – Order of nodes along a path; determines start/end of stroke stitches. Reverse path to flip direction.
- **Rungs** – Direction lines on a satin column that control stitch angle; used in manual satin with the rung method.
- **Rails** – The two boundary paths of a satin column. Must have matching path direction for correct rendering.
- **Jump stitch** – Movement of the needle without sewing (travel from one element to the next). Too many or long jumps hurt quality and speed; prefer routing so connections are sewn (e.g. jump-to-stroke) instead of hiding with trims only.
- **Stitch order** – Order in which elements are sewn. Affects registration, puckering, and thread changes. Use “Re-stack elements in selected order” and start/end commands to control it.

---

## Errors and checks

- **Troubleshoot Objects** – Ink/Stitch extension that marks errors (red) and warnings (yellow) with suggested fixes. Can detect errors, warnings, and object-type warnings.
- **Path errors** – Issues that prevent correct rendering: e.g. invalid path, wrong path direction, crossing borders (now often a warning), too-small shapes, missing or conflicting params.
- **Cleanup Document** – Removes very small shapes and leftover objects that can cause errors; configurable threshold and optional empty layer/group removal.

---

## Params and SVG

- **Params** – Ink/Stitch settings per object (density, underlay, pull comp, stitch length, etc.). Stored in SVG; edited via Extensions > Ink/Stitch > Params.
- **Presets** – Saved param sets that can be loaded for reuse.
