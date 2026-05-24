# Wilcom EmbroideryStudio – summary (for analyzers)

Key terms and object-group settings from the collected Wilcom docs. Use with [issue-checker-cross-reference.md](../../rules/issue-checker-cross-reference.md) when implementing checks.

**Source docs:** [docs/README.md](../../README.md) → Sources: Wilcom. Collected 2026-02-20.

---

## 1. Object groups (fabric settings)

| Group | Use | Main params |
|-------|-----|-------------|
| **Tatami / Program Split** | Fill: large/irregular shapes (Tatami = rows of run stitches); decorative program split | Length, Spacing; underlay type; pull compensation |
| **Wide Satin** | Larger satin objects | **Density slider** (single control); underlay; pull comp |
| **Narrow Satin** | Narrow satin objects | Density slider; underlay (often different type than wide) |
| **Lettering** | Lettering objects | Same idea as Satin |

Defaults come from: **Auto Fabric** (on) → fabric settings; **preset styles** (when “use preset styles” on); **templates** (when both off).

---

## 2. Underlay

- Needed for: stabilization, loft, reducing puckering/pull; flattening napped fabric. Prefer automatic underlay over just increasing density.
- Stored per object; regenerated on scale/transform. Separate from cover stitch settings.
- **Default underlay:** Auto Fabric → from fabric; or preset styles; or template. See [underlay-types.md](underlay-types.md).

---

## 3. Pull compensation

- Counters inward pull by **overstitching** outlines on the penetration side. Adjust in **Object Properties** docker.
- Underlay + backing + topping also reduce push-pull. See [compensating-fabric-stretch.md](compensating-fabric-stretch.md).

---

## 4. Density

- **Tatami/Program Split:** Length and Spacing (similar to row spacing).
- **Satin:** Single **density** setting (slider), not separate length/spacing. See [manage-fabrics.md](manage-fabrics.md).

---

## 5. Stabilizer

- Per fabric: recommended stabilizer(s) and description in **Manage Auto Fabrics** → Stabilizer tab; shown in Choose Fabric dialog.

---

## 6. URL → local file (Wilcom)

| Topic | Local file |
|-------|------------|
| Underlay & pull comp overview | underlay-pull-compensation.md |
| Stabilizing with automatic underlay | stabilizing-automatic-underlay.md |
| Underlay types | underlay-types.md |
| Compensating for fabric stretch | compensating-fabric-stretch.md |
| Manage fabrics | manage-fabrics.md |
