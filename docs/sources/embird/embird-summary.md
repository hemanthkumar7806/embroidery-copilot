# Embird Studio – summary (for analyzers)

Key terms and parameter structure from the collected Embird Studio manual. Use with [issue-checker-cross-reference.md](../../rules/issue-checker-cross-reference.md) when implementing checks.

**Source docs:** [docs/README.md](../../README.md) → Sources: Embird. Collected 2026-02-20.

---

## 1. Object types and parameter tabs

| Tab | Applies to | Main params |
|-----|------------|-------------|
| **Whole Design** | All objects (global) | Additional Density, Additional Pull Compensation; underlay offset (Edge, Zig-Zag); min/max underlay length |
| **Fill** | Fill objects | Density, Pull Compensation; Edge/Zig-Zag underlays; Plain Fill, Motifs, Auto Column |
| **Column** | Column (satin) objects | Density, Pull Compensation; Center/Edge/Zig-Zag underlay; Auto Select Underlay |

Other tabs: All Selected, Column with Pattern, Outline, Manual Stitches, Connection, Applique, Sfumato.

---

## 2. Underlay types (Embird)

| Type | Use |
|------|-----|
| **Center** | Small or thin column objects; underlay along center |
| **Edge** | Medium/large objects; runs along edge (Edge Walk for fill) |
| **Zig-Zag** | With edge for large or thick objects; grid of loose stitches |

Global **Offset of Edge Underlay** and **Offset of Zig-Zag Underlay** (Whole Design > Offset tab): absolute (mm) or scaled (%). Per-object offset for fills, columns, appliques.

---

## 3. Density

- **Definition:** Distance between needle points in 0.1 mm grid. Density 4.0 = 0.4 mm. Typical satin/fill approx. 3.0–4.0.
- **Fill:** Distance between rows of stitches or motifs; default from Default Thread Weight in Preferences.
- **Additional Density (Whole Design):** Adjust whole design at once for different thread.

---

## 4. Pull compensation

- Per object: **Pull Compensation** (Fill and Column tabs) – extension of stitches on edge for thread pull (elastic) or sinkage (fleece).
- **Additional Pull Compensation (Whole Design):** Adjust whole design at once for elastic fabric or sinkage.

---

## 5. Stitch order / connections

- Object order and start/end points matter; add **connections** between objects to minimize jumps. See [digitizing-get-started.md](digitizing-get-started.md).

---

## 6. URL → local file (Embird)

| Topic | Local file |
|-------|------------|
| Parameters overview | parameters-overview.md |
| Whole design (global density, pull comp, underlay offset) | parameters-whole-design.md |
| Fill | parameters-fill.md |
| Column | parameters-column.md |
| Digitizing get started | digitizing-get-started.md |
