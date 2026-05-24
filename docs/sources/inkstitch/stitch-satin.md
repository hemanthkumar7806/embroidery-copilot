# Satin Stitch - Ink/Stitch

- **Source:** https://inkstitch.org/docs/stitches/satin-column/
- **Collected:** 2026-02-20

**Summary:** Satin columns are zigzag stitches between two rails; width is the distance between rails. Documents creation methods (stroke-to-satin, fill-to-satin, manual with rungs), params (zig-zag spacing, pull compensation, max stitch length), and three underlay types: center-walk, contour, and zig-zag (often combined for “German underlay”).

---

# Content from https://inkstitch.org/docs/stitches/satin-column/

Satin Stitch - Ink/Stitch

## What it is

Satin stitch is used for borders, letters or small fill areas.

## How to create

Ink/Stitch offers several option to create satin columns. Methods 1 to 4 create convert to a manual satin column which then can be modified as necessary. Method 5 allows for more customization.

1. Manual Satin Column: take full control over every part of the satin column
2. Fill to Satin: create satin columns from fills
3. Zigzag to Satin: satin column creation for graphic tablets and touch screens
4. Stroke to Live Path Effect Satin: modifiable satin column with optional patterned outline
5. Stroke to Satin: for equal width satin columns
6. Sample Files Including Satin Column

### Method 1 - Stroke to Satin

This method takes a stroke or a path and converts it to a satin column.

#### Option 1

Using this option, a contour is added to stroke/path using the offset function. The countor creates a new path around the outside of the line. The contour can be set to the width of the desired satin column. Using`Extensions > Ink/Stitch > Satin Tools > Convert Stroke to Satin`, the satin columns will be created, including the rungs, which can be adjusted. Optionally, use autoroute to optimize`Extensions > Ink/stitch > Satin Tools > Auto-route Satin...`

Get more information about [Stroke to Satin](https://inkstitch.org/docs/satin-tools/#convert-line-to-satin)

This feature will be part of an upcoming Ink/Stitch release. It is not yet integrated in Ink/Stitch.

#### Option 2

Using this option, a contour is added to stroke/path using the offset function. The contour creates a new path around the outside of the line. The contour can be set to the width of the desired satin column. Using `Extensions > Ink/Stitch > Params, open the Satin Column Tab and activate Custom Satin Columns.

With Option 2, the position of the nodes can influence how the satin will be rendered:

### Method 2 - Stroke to Live Path Effect Satin

This can be used to create a satin which can either have a patterned outline or to create a satin which is more easily to adapt in width. Please note, that once you use auto-routing on this type of satin, the live path effect will be applied and the path can only be adapted manually afterwards.

Use`Path > Object to path` to convert this to a standard satin column.

Get more information about [Live Path Effect Satins](https://inkstitch.org/docs/satin-tools/#stroke-to-live-path-effect-satin)

### Method 3 - Zigzag Line to Satin

This method is convenient when you use a a touch screen or graphic tablet.

Get more information about [Zigzag to Satin](https://inkstitch.org/docs/satin-tools/#zigzag-line-to-satin)

### Method 4 - Fill to Satin

Fill to Satin can be used to convert a fill into a satin stitch. It is a semi-automatic function and requires additional manual work.

Get more information about [Fill to Satin](https://inkstitch.org/docs/satin-tools/#fill-to-satin)

### Method 5 - Manual Satin Column

A satin column is defined by a shape made of two mostly-parallel lines. Ink/Stitch will draw zig-zags back and forth between the two lines. The thickness of the column will be based on the distance between the two lines.

[Check path directions](https://inkstitch.org/docs/customize/#enabling-path-outlines--direction). For the satin column to work, they have to be equal.

If they are not equal, select one point of one subpath with the Node Editor Tool (`N`) and run`Path > Reverse`. This will reverse only the selected subpath.

- Then select your satin column and run params through`Extensions > Ink/Stitch > Params` or a [custom shortcut key](https://inkstitch.org/docs/customize/).
- Use node or rung method as described below.
- Combine two strokes with`Path > Combine` or hit`Ctrl+K`.

#### Node Method

Depending on the complexity of your design, this method might be time consuming, because the two paths must have the same number of points. This means that each path will be made up of an equal number of Bezier curves. Each pair of points acts as a "checkpoint": Ink/Stitch will ensure that a "zag" ends up going from one point to the other.

#### Rung Method

The rung method will give you more control over the way the satin column is rendered. Good positioning of points on each of the two lines helps getting the stitch directions right. However, there are situations where you need to add direction lines ("rungs") for satin columns:

- Special situations where you want the stitch directions to be weird
- Complicated drawings where moving points is both difficult and time consuming
- Some tricky corner areas

Manual adding of rungs

Click a second time at the end of the rung.

Original design by [Liv Iko](https://thenounproject.com/liv_iko/collection/birds/?i=898697) edited by [EDUTECH Wiki](https://edutechwiki.unige.ch/en/InkStitch)

- Click once at the start of the rung.
- Hold`Shift`.
- Press`P` or select the Pencil Tool.
- Make sure the existing satin column path (with the two subpaths) is selected with the Node Editor tool.

Info: We strongly recommend to use at least three rungs. If you use exactly two rungs (and two rails) it is hard for Ink/stitch to decide which is which.

## Start and end position

Satin columns automatically start at the nearest point to the previous element and end at the nearest point to the next element.

To disable this behavior open the [params dialog](https://inkstitch.org/docs/params/) and disable one or both of the`start/end at nearest point` options.

Alternatively add a start or end point manually by attaching a [command](https://inkstitch.org/docs/commands/#attach-commands-to-selected-objects-) to the satin column.

## Params

Running`Extensions > Ink/Stitch > Params` will give you the possibility to fine-tune your satin column and to use underlay.

Satin Column supports three kinds of underlay, of which you can use any or all simultaneously.

Read also [this excellent article](https://www.mrxstitch.com/underlay/) on satin column design.

### Asymmetrical parameter

Some satin column parameters are asymmetrical, meaning that different values ​​can be applied to the two rails.

For example, the "Random percentage of satin width increase" is an asymmetrical parameter. If a single value is entered, it applies to both rails; if two values ​​are entered separated by a space, the first applies to the first rail, and the second applies to the second rail.

Some of these params are not part of the recent release.

### Satin Top Layer

Some parameters will be part of an upcoming Ink/Stitch release. It is not yet integrated in Ink/Stitch.

| Settings | Description |
| --- | --- |
| Custom satin column | ☑ | Must be enabled for these settings to take effect. |
| Method | Chose`Satin Column` |
| Short stitch inset | Stitches in areas with high density will be inset by this amount (%) Short stitch inset can take multiple values separated by a space. When multiple values are set, the satin column will use these to level consecutive short stitches |
| Short stitch distance | Inset stitches if the distance between stitches is smaller than this (mm). |
| Zig-Zag spacing | the peak-to-peak distance between zig-zags |
| Pull compensation percentage | Additional pull compensation which varies as a percentage of stitch width. Two values separated by a space may be used for an asymetric effect. |
| Pull compensation | Satin stitches [pull the fabric together](https://inkstitch.org/tutorials/push-pull-compensation/), resulting in a column narrower than you draw in Inkscape. This setting expands each pair of needle penetrations outward from the center of the satin column by a fixed length. Two values separated by a space may be used for an asymetric effect. |
| Reverse rails | Enabling this may help if your satin renders very strangely. Options are : ◦ Automatic, the default value aims to detect and fix the problem ◦ Don't reverse , disable automatic detection ◦ Reverse first rail ◦ Reverse second rail ◦ Reverse both rails |
| Swap rails | ☑ | Swaps the first and the second rails of a satin column. Affecting which side the thread finishes on as well as any other sided property. |
| Stitch length | Stitch length (in mm) of the underpaths (connecting lines to the start or end point) |
| Tolerance | Decreasing tolerance helps the underlay to stay behind the top level. However too small a tolerance may create very short stitches. |
| Running stitch position | Position of underpath from between the rails. 0% is along the first rail, 50% is centered, 100% is along the second rail. |
| Start at nearest point | Start at nearest point to the previous element. A start position command will overwrite this setting. |
| End at nearest point | End at nearest point to the next element. An end position command will overwrite this setting. |
| Random percentage of satin width increase | Lengthen stitch across rails at most this percent. Two values separated by a space may be used for an asymetric effect. |
| Random percentage of satin width decrease | Shorten stitch across rails at most this percent. Two values separated by a space may be used for an aysmmetric effect. |
| Random zig-zag spacing percentage | Amount of random jitter added to zigzag spacing |
| Split Method | Options: ◦ default ◦ Simple ◦ Staggered |
| Maximum stitch length | Stitches wider than this will be split up (split stitches). |
| Random Jitter for split stitches | Randomizes split stitch length if random phase is enabled, stitch position if disabled. |
| Random Phase for split stitches | ☑ | Controls whether split stitches are centered or with a random phase (which may increase stitch count). |
| Stagger this many times before repeating | Stitches are staggered so that neighboring rows of stitches don't all fall in the same column (which would create a distracting valley effect). Setting this dictates the length of the cycle by which successive stitch rows are staggered. Fractional values are allowed and can have less visible diagonals than integer values. Active only when split method is staggered |
| Minimum length for random-phase split | Defaults to maximum stitch length. Smaller values allow for a transition between single-stitch and split-stitch. |
| Random seed | Use a specific seed to compute stitch plan. If empty, the seed is the element ID . Re-roll if you are not happy with the result. |
| Minimum stitch length | Overwrite global minimum stitch length setting. Shorter stitches than that will be removed. |
| Minimum jump stitch length | Overwrite global minimum jump stitch length setting. Shorter distances to the next object will have no lock stitches |
| Allow lock stitches | ☑ | Enables lock stitches in only desired positions |
| Force lock stitches | ☑ | Sew lock stitches after sewing this element, even if the distance to the next object is smaller than defined in the collapse length value value in the Ink/Stitch prefreneces. |
| Tack stitch | Chose your [favorite style](https://inkstitch.org/docs/stitches/lock-stitches/) |
| Lock stitch | Chose your [favorite style](https://inkstitch.org/docs/stitches/lock-stitches/) |
| Stop After | ☑ | Stop the machine after sewing this object. Before stopping it will jump to the stop position (frame out) if defined. |
| Trim After | ☑ | Trim the thread after sewing this object. |

### Center-Walk Underlay

This is a row of running stitch down the center of the column and back. This may be all you need for thin satin columns. You can also use it as a base for more elaborate underlay.

| Settings | Description |
| --- | --- |
| Stitch length | Length of stitches (in mm) |
| Tolerance | Decreasing tolerance helps the underlay to stay behind the top level. However too small a tolerance may create very short stitches. |
| Repeats | Odd numbers of repeats will reverse the stitch direction of the satin column, causing it to start and end at the same position. |
| Position | Position of underlay from between the rails. 0% is along the first rail, 50% is centered, 100% is along the second rail. |

### Contour Underlay

This is a row of running stitch up one side of the column and back down the other. The rows are set in from the edge of the column by an amount you specify. For small or medium width satin, this may serve well enough by itself.

| Settings | Description |
| --- | --- |
| Stitch length | Length of stitches (in mm) |
| Tolerance | Decreasing tolerance helps the underlay to stay behind the top level. However too small a tolerance may create very short stitches. |
| Inset distance (fixed) | Shrink the outline by a fixed length, to prevent the underlay from showing around the outside of the satin column. Negative values are possible. |
| Inset distance (proportional | Shrink the outline by a proportion of the column width, to prevent the underlay from showing around the outside of the satin column. Negative values are possible. |

### Zig-Zag Underlay

This is essentially a lower-density satin stitch sewn to the end of the column and back to the start. Added with contour underlay, you get the "German Underlay" mentioned in [this article](https://www.mrxstitch.com/underlay/). For wide columns or challenging fabrics, you can use all three underlay types together.

| Settings | Description |
| --- | --- |
| Inset amount (proportional) | Inset to cover the underlay entirely by the top layer. Negative values are possible. Default: half of contour underlay inset. It is possible to enter two space separated values to define different values for each side. |
| Inset amount (fixed) | Inset to cover the underlay entirely by the top layer. Negative values are possible. Default: half of contour underlay inset. It is possible to enter two space separated values to define different values for each side. |
| Maximum stitch length | Stitches wider than this will be split up (split stitches). |
| Zig-Zag spacing | The peak-to-peak distance between zig-zags. |

## Satin Tools

Make sure to have a look at the [Satin Tools](https://inkstitch.org/docs/satin-tools/). They will make your life with Satin Columns a lot easier.

## Sample Files Including Satin Column

[AppliqueApplique example file](https://inkstitch.org/tutorials/applique/)

[Free Standing Lace - ButterflyFree Standing Lace - Butterfly](https://inkstitch.org/tutorials/fsl/)

[FringeFringe example file](https://inkstitch.org/tutorials/fringe/)

[Ink/Stitch Logo & Branding GuideInk/Stitch logo as SVG file, digitized version and branding guide.](https://inkstitch.org/tutorials/resources/inkstitch-logo/)

[Monogram FrameMonogram Frame Example](https://inkstitch.org/tutorials/monogram/)

[Multicolor SatinSimulating multicolor satin collumns](https://inkstitch.org/tutorials/multicolor_satin/)

[PuffPuff example file](https://inkstitch.org/tutorials/puff/)

[Random SatinRandom Satin](https://inkstitch.org/tutorials/random_satin/)

[Satin Stitch EdgesSample file for satin stitch edges](https://inkstitch.org/tutorials/satin-edges/)

[Software Freedom DaySoftware Freedom Day example file](https://inkstitch.org/tutorials/software-freedom-day/)

[Using distort path effectsUsing distort paths effects](https://inkstitch.org/tutorials/distort/)
