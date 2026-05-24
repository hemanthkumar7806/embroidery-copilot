# Troubleshoot passes but design won’t stitch out (r/Inkstitch)

- **Source:** Community reports ([r/Inkstitch](https://www.reddit.com/r/Inkstitch/)).
- **Collected:** 2026-02

**Summary:** Real-world case where an SVG passes Ink/Stitch Troubleshoot but view stitch plan, simulator, or save as PES causes Inkscape/Ink/Stitch to freeze or take a very long time (e.g. 20+ minutes). Use this when building or extending an issue checker: even if Troubleshoot is not run, flag geometry and stitch-type patterns that can cause this.

---

## What happened

- User ran **Troubleshoot Objects** – no errors reported.
- **Stitch plan preview**, **Simulate**, or **Save as PES** caused the application to freeze (or take more than 20 minutes to complete).
- On a more powerful machine, the file eventually saved after over 30 minutes.

---

## Quoted highlights from the thread

- *“One fill object has a lot of narrow pathing where it is not possible for inkstitch to create a proper stitch … this file needs to be completely redigitized … a lot of other objects … are not connected with each other and every thing is done in fill stitching what for a lot of the objects is not an appropriate stitch type.”*
- *“That design contains SO MANY nodes, that inkscape will need a 100 years to calculate an algorithm to fill the shapes. Especially the black is poorly digitized … trace bitmap of a picture, or … the vector file came exactly like that and you did nothing to optimize.”*
- *“Make the yellow one big continuous shape … remove the black ‘holes’ in the yellow shape. And the black, you should manually turn into lines. The thick lines on the outside could be satin stitches, while the thin lines for the scales can be running stitches on top of the yellow color.”*
- *“Inkscape doesn’t freeze. I tried it. It literally takes more than 20 minutes to calculate some of those paths, but eventually it finishes.”*

---

## Mapping to issue types (for issue checker)

| Issue type | What to check | Use in checker |
|------------|----------------|----------------|
| **Excessive nodes** | High node count (or segment count) on path elements; suggest simplifying or reducing nodes. | Use `get_design_report` with `include_geometry=true`; warn if `node_count` &gt; 1000 (or configurable threshold). |
| **Narrow fill pathing** | Fill object has regions too narrow for the fill algorithm to lay stitches; can cause long runtimes or freeze. | No direct metric in SVG; document as a known cause; suggest converting narrow areas to satin or running stitch. |
| **Troubleshoot passes but export/stitch plan hangs** | Design is valid for Troubleshoot but stitch generation is impractical. | Combination of excessive nodes + overuse of fill; warn even when Troubleshoot is not run. |
| **Overuse of fill** | Many or all objects set as fill when satin (columns) or running/bean (lines, details) would be more appropriate. | Count fill vs satin vs stroke in design report; if almost all fill, suggest reviewing stitch types (satin for thick lines, running for thin lines/details). |

When you add a new check to the issue checker, consult the cross-reference and this doc so the AI can warn users about these patterns before they hit a freeze or very long export.
