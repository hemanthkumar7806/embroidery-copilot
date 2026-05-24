# Hatch Embroidery 3 – summary (for analyzers)

Key terms and object-group settings from the collected Hatch docs. Use with [issue-checker-cross-reference.md](../../rules/issue-checker-cross-reference.md) when implementing checks.

**Source docs:** [docs/README.md](../../README.md) → Sources: Hatch. Collected 2026-02-20.

---

## 1. Object groups (fabric settings)

| Group | Use | Main params |
|-------|-----|-------------|
| **Tatami / Embossed Fill** | Fill: large/irregular shapes; embossed effects | Length, Spacing; underlay type; pull compensation |
| **Wide Satin** | Larger satin objects | Density; underlay; pull comp |
| **Narrow Satin** | Narrow satin objects | Density; underlay (often different type than wide) |
| **Lettering** | Lettering objects | Same idea as Satin |

Defaults from: **Auto Fabric** (selected in Customize Design > Auto Fabric) or **template**. Custom fabrics: Software Settings > Manage Auto Fabrics.

---

## 2. Underlay types (Hatch naming)

| Type | Purpose |
|------|---------|
| **Center Run** | Narrow columns, e.g. 2–3 mm wide |
| **Edge Run** | Larger shapes such as letters; good for knits |
| **Zigzag** | Wide columns; stitch length adjustable |
| **Tatami** | Large filled shapes; rows across object |

Dual underlays: Underlay 1 + Underlay 2 (e.g. Edge Run with Tatami or Zigzag). Default underlay from auto fabric or template. Larger areas and stretchy fabrics need more underlay.

---

## 3. Pull compensation

- Auto Fabric applies a calculated amount automatically. Adjust overstitching in **Object Properties** for varying fabric stretch.
- Underlay, backing, and topping also reduce push-pull. See [pull-compensation.md](pull-compensation.md).

---

## 4. Density

- **Adjust Stitch Spacing:** Customize Design / Edit Objects > Adjust Stitch Spacing. Percentage adjustment (e.g. 200% to reduce density). Use for different fabric/thread or to reduce stitch count.
- Object-group defaults (Tatami/Embossed Fill, Wide/Narrow Satin, Lettering) set in Fabric Settings via Manage Auto Fabrics.

---

## 5. Stabilizer / backing

- Auto Fabric dialog shows **recommended stabilizers** per fabric. Backings: cut-away, tear-away, wash-away (soluble). Tear-away for woven; cut-away for knits. Manage fabrics: add recommended stabilizers and description.

---

## 6. URL → local file (Hatch)

| Topic | Local file |
|-------|------------|
| Automatic underlay | automatic-underlay.md |
| Pull compensation | pull-compensation.md |
| Adjust stitch densities | adjust-stitch-densities.md |
| Manage fabrics | manage-fabrics.md |
| Choose auto fabrics | choose-auto-fabrics.md |
