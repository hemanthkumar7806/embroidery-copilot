# Community – extracted data (for analyzers)

Concrete numbers, failure-cause list, fabric→tip mapping, and URL→file mapping from community sources. Use as a single data reference for issue checks that supplement official docs (e.g. density by fabric, real-world failure causes).

**Sources:** Curated from blogs (DigitizingUSA, The Embroidery Cloud, Hooping Station, Embroiplanet, Hatchembroidery), forums (Reddit r/Machine_Embroidery, general best practices), and YouTube (digitizing tutorials, pull compensation). Collected 2026-02-20. **Topic files (common-mistakes.md, fabric-presets.md, failure-causes.md) contain pasted content from each source** so AI/analyzers can retrieve the data without opening URLs; each tip has “Content from source” plus the link.

---

## 1. Numeric rules (density, spacing, pull comp)

| Param | Value / range | Context | Source file |
|-------|----------------|---------|-------------|
| Row spacing (fill), general | 0.4–0.6 mm | Most designs | fabric-presets.md |
| Row spacing, cotton | 0.4–0.5 mm | T-shirts, polos | fabric-presets.md |
| Row spacing, fleece | 0.5–0.6 mm | With light underlay | fabric-presets.md |
| Row spacing, hoodie / high-pile | Looser than cotton; “never above 0.5 mm” often cited | Avoid stiffness | fabric-presets.md |
| Row spacing, leather | 0.6–0.8 mm | Avoid holes | fabric-presets.md |
| Row spacing, silk/satin | 0.6–0.7 mm | Avoid puckering | fabric-presets.md |
| Row spacing, denim | 0.3–0.4 mm | Heavy fabric | fabric-presets.md |
| Small text / details | 0.6–0.8 mm | Under ~0.25 in; cap small text 0.7 mm | common-mistakes.md, fabric-presets.md |
| Satin column width, min | 1.5 mm | Below = thread breaks, needle deflection | fabric-presets.md |
| Satin column width, sweet spot | 2–9 mm | Typical range | fabric-presets.md |
| Satin column width, max (auto-convert) | ~12.1 mm | Many algorithms convert to jump | fabric-presets.md |
| Pull compensation, starting | 0.17–0.20 mm | Tutorial/video; increase for stretchy/large | fabric-presets.md, failure-causes.md |
| Pull compensation, default / auto | 0.2 mm default; 0.4 mm for auto digitizing | Software/YouTube guidelines | common-mistakes.md, failure-causes.md |
| Pull compensation, range | 0.1–0.4 mm | By density, fabric, tension, element thickness | common-mistakes.md, failure-causes.md |
| Density trim (fix overload) | Reduce 10–15% | When puckering/breaks | common-mistakes.md |
| Running stitch length, min | 0.5 mm | Below = thread breaks (machine thinks same place) | youtube-dataset.md (Video 2) |
| Running stitch length, safe zone | 1 mm | Orange zone; 1.5 mm green zone | youtube-dataset.md (Video 2) |
| Satin width, wearable | 1.5–7 mm | 1 mm can disappear on terry/sherpa; 1.5 mm safety; Video 2 cites 5–7 mm for wearable | youtube-dataset.md (Video 2) |
| Satin width, non-wearable | 7–12 mm | — | youtube-dataset.md (Video 2) |
| Stitch length trim threshold | 12.1 mm | Machine trimmers activate above this | youtube-dataset.md (Video 2) |
| Default density (often overused) | 0.4 | Reduce density on each layer when stacking | youtube-dataset.md (Video 2) |
| Vinyl / leather | Less density | Too many penetrations cut through | youtube-dataset.md (Video 2), fabric-presets.md |
| Sherpa / terry cloth | More density | High pile needs more to cover fabric | youtube-dataset.md (Video 2), fabric-presets.md |
| Bean / run (line art) | 2.4–2.5 mm | Above 2.6 = uneven stitch length | youtube-dataset.md (Video 5) |

---

## 2. Failure causes (short list)

| Cause | Effect (short) | Detail in |
|-------|----------------|-----------|
| Too much density | Puckering, stiffness, thread breaks | failure-causes.md |
| No / wrong underlay | Sinking, gaps, weak structure | failure-causes.md |
| Wrong / missing pull comp | Puckering, gaps, design sews small | failure-causes.md |
| Bad pathing / stitch order | Jumps, misalignment, breaks | failure-causes.md |
| Wrong stitch type | Poor coverage, breaks, uneven | failure-causes.md |
| Wrong fabric settings | Puckering or lost on wrong fabric | failure-causes.md |
| Stabilizer / hooping | Shifting, misalignment | failure-causes.md |

---

## 3. Fabric → tips / presets (all cloth types)

| Fabric / cloth | Density (mm) | Underlay | Pull comp | Notes |
|----------------|--------------|----------|-----------|------|
| Cotton | 0.4–0.5 | Standard | Standard | T-shirts, polos |
| Fleece | 0.5–0.6 | Light | — | Medium density |
| Hoodie (example thick knit) | Looser than cotton | Edge run; Zigzag+Edge for stretch | Increase | Don’t pack like cotton |
| Leather | 0.6–0.8 | — | — | Simple designs |
| Silk / satin | 0.6–0.7 | Yes, stability | — | Avoid puckering |
| Denim | 0.3–0.4 | Standard | — | Heavy fabric |
| Terry / towel | +10–20% from standard | Zig-zag; Edge+Zig-zag for columns &gt;3 mm; cross-stitch for fill | Increase with column thickness | Mat down pile |
| Twill | Standard | Edge Run or Zigzag | — | Stable |
| Canvas | Standard | Edge Run or Zigzag | — | Stable |
| Drill | — | Less underlay | — | Firm fabric |
| Pique | — | More underlay; edge runs | — | Like knits |
| Vinyl | Less density | — | — | Avoid holes |
| Sherpa / high-pile | More spacing | More underlay | — | Prevent stiffness |
| Cap | 0.5 main, 0.7 small text | — | — | Clarity for text |
| Plush | — | More underlay | — | Test on scrap |

---

## 4. URL → file mapping

| URL | Primary file(s) |
|-----|------------------|
| https://www.digitizingusa.com/showblog/stitch-density-in-embroidery-digitizing | common-mistakes.md, fabric-presets.md, failure-causes.md |
| https://theembroiderycloud.com/top-7-common-embroidery-digitizing-mistakes-and-how-to-avoid-them/ | common-mistakes.md, failure-causes.md |
| https://hoopingstation.com/blogs/articles/the-ultimate-embroidery-digitizing-cheat-sheet-density-underlay-pull-comp-and-objects-explained-for-real-stitch-out-results | common-mistakes.md, fabric-presets.md, failure-causes.md |
| https://hatchembroidery.com/resources/blog/what-you-need-to-know-about-pull-compensation | failure-causes.md |
| https://hatchembroidery.com/resources/blog/how-to-choose-the-right-underlay-for-your-machine-embroidery-designs | common-mistakes.md, fabric-presets.md, failure-causes.md |
| https://embroiplanet.com/common-embroidery-problems-caused-by-poor-digitizing-and-how-to-fix-them/ | common-mistakes.md, failure-causes.md |
| https://www.youtube.com/watch?v=Is5A47QQakI (Push and Pull Compensation – digitizing for beginners) | common-mistakes.md, failure-causes.md |
| https://youtube.com/watch?v=3xpLqGkHHQM (FREE Embroidery Digitizing 101 Course) | fabric-presets.md, youtube-dataset.md § Video 2 |
| https://www.youtube.com/watch?v=Pr_Du4rbxDE (How to Digitize a Logo for Beginners) | youtube-dataset.md § Video 3 |
| https://www.youtube.com/watch?v=ie9ArCsHtZc (Learn to Digitize for Machine Embroidery) | youtube-dataset.md § Video 4, common-mistakes.md, failure-causes.md |
| https://www.youtube.com/watch?v=zwfIuDRhN2k (Digitizing Line Art – Embrilliance StitchArtist) | youtube-dataset.md § Video 5 |
| https://www.digitizingusa.com/showblog/pull-and-push-compensation-in-embroidery | common-mistakes.md |
| https://www.digitizingmadeeasy.com/embroidering-on-terry-cloth-digitizing-tips-techniques/ | fabric-presets.md |
| YouTube transcripts (Transcript API) | [youtube-dataset.md](youtube-dataset.md) – use curl to fetch; paste extracted content there |

Forums / Reddit r/Machine_Embroidery and general best practices are cited in topic files. **Fabric list:** hoodie is one example among many; see fabric-presets.md § All fabric types for cotton, fleece, denim, leather, silk, satin, knits, terry/towel, twill, canvas, drill, pique, vinyl, sherpa, cap, plush, etc. **YouTube:** fetch transcript with Transcript API (curl); see youtube-dataset.md.
