# Running Stitch - Ink/Stitch

- **Source:** https://inkstitch.org/docs/stitches/running-stitch/
- **Collected:** 2026-02-20

**Summary:** Running stitch follows a path with small stitches. Params: running stitch length, tolerance, repeats (odd/even for end position), bean stitch repeats, randomize length (for Moiré avoidance), min stitch length, lock/tack stitches. Path direction affects stitch direction; use Autoroute Running Stitch and Redwork for routing.

---

# Content from https://inkstitch.org/docs/stitches/running-stitch/

Running Stitch - Ink/Stitch

## What is it?

Running stitch produces a series of small stitches following a line or curve.

## How to create it

Running stitch is created from a path with a stroke color.

The stitch direction is impacted by the [path direction](https://inkstitch.org/docs/customize/#enabling-path-outlines--direction). If you want to change the starting and ending point of your running stitch, use`Path > Reverse`.

If an object consists of multiple paths, they will be stitched in order with a jump between each.

## Parameters

Some parameters will be part of an upcoming Ink/Stitch release. It is not yet integrated in Ink/Stitch.

Open`Extensions > Ink/Stitch > Params` to update the parameters.

| Setting | Description |
| --- | --- |
| Running stitch along paths | Must be selected to use these settings. |
| Method | Determines which stitch to use. Select`Running stitch / Bean stitch` |
| Repeats | Defines how many times to stitch along the path◦ Default: 1 (traveling once from the start to the end of the path)◦ Odd number: stitches will end at the end of the path◦ Even number: stitching will return to the start of the path |
| Bean stitch number of repeats | Determines the number of times to repeat each stitch.◦ A value of '0' does not repeat the stitch (normal stitch)◦ A value of '1' repeats each stitch three times (forward, back, forward).◦ A value of '2' repeats the stitch six times. ◦ See [Bean Stitch Mode](https://inkstitch.org/docs/stitches/bean-stitch/) for more information |
| Running stitch length | Determines the length of stitches. By entering multiple values, it is possible to define a custom stitch length pattern. For instance`2 4` will create stitches of length alternatively 2 and 4 mm. |
| Running stitch tolerance | Determines the acceptable distance from the path. A lower tolerance will bring the stitches closer together. A higher tolerance allows for stitches to be farther away from the path. A higher tolerance may mean sharp corners may be rounded. |
| Randomize stitch length | Allows for randomize stitch length. This is recommended for closely-spaced curved fills to avoid Moiré artefacts. |
| Random stitch length jitter | Only available if`Randomize stitch length` is selected. Determines the variation in the length of each stitch. |
| Random Seed | Rolling the dice or setting a new value will change the random stitches |
| Minimum stitch length | Overwrites the global minimum stitch length setting. Stitches small than this value will be removed. |
| Minimum jump stitch length | Overwrites the global minimum jump stitch length setting. Shorter distances to the next object will have no lock stitches. |
| Allow lock stitches | Enables lock stitches in only desired positions |
| Force lock stitches | Determines if lock stitches are sewn after this element, even if the distance to the next object is smaller than defined in the Collapse Length value in the Ink/Stitch preferences. |
| Tack stitch | Determines the type of tack stitch. Tack stitches are small stitches at the beginning of a stitch. They help to secure the beginning of the thread. [favorite style](https://inkstitch.org/docs/stitches/lock-stitches/) |
| Lock stitch | Determines the type of lock stitch. Lock stitches are small stitches at the end of stitch. They help to secure the end of the thread. [favorite style](https://inkstitch.org/docs/stitches/lock-stitches/) |
| Trim After | Determines if the thread is trimmed after sewing this object. |
| Stop After | Determines if the machine is stopped after sewing this object. Before stopping it will jump to the stop position (frame out) if defined. |

## Routing

For better stitch routing try the extensions`Autoroute Running Stitch` and`Redwork` in the [stroke tools](https://inkstitch.org/docs/stroke-tools/).

## Patterned Running Stitch

Read the [tutorial](https://inkstitch.org/tutorials/patterned-unning-stitch/) how to create a patterned running stitch.

## Sample Files Including Running Stitch

[AppliqueApplique example file](https://inkstitch.org/tutorials/applique/)

[Cookie Cutter TilingUsing Tiling LPE, clipping path and autorouting to achieve Pattern Fill](https://inkstitch.org/tutorials/cookie_cutter_tiling/)

[Free Standing Lace - ButterflyFree Standing Lace - Butterfly](https://inkstitch.org/tutorials/fsl/)

[FringeFringe example file](https://inkstitch.org/tutorials/fringe/)

[Ink/Stitch Logo & Branding GuideInk/Stitch logo as SVG file, digitized version and branding guide.](https://inkstitch.org/tutorials/resources/inkstitch-logo/)

[Life Flower Auto route running stitches](https://inkstitch.org/en/tutorials/autoroute_life_flower/)

[MandalaMandala and Embroidery](https://inkstitch.org/tutorials/mandala/)

[Monogram FrameMonogram Frame Example](https://inkstitch.org/tutorials/monogram/)

[Patterned Running StitchHow to create a patterned running stitch with Inkscapes live path effects](https://inkstitch.org/tutorials/patterned-unning-stitch/)

[Stitching the Inkscape 1.4 Splash Screen LogoOriginal design by Inkonic](https://inkstitch.org/tutorials/inkscape-splash/)

[Unicorn with auto-route running stitchAuto-route running stitch Unicorn](https://inkstitch.org/tutorials/autoroute_unicorn/)
