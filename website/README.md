# Inkscape AI website

Static, plain HTML/CSS/JS download & marketing site for the Inkscape AI
extension. No build step, no dependencies — just files you can open directly
or deploy to any static host.

## Local preview

```bash
cd website
python -m http.server 8080
```

Then open http://localhost:8080.

## Building the download zip

The zip is built from `inkscape_extension/` and is never committed — build it
before deploying:

```bash
python scripts/build_extension_zip.py
python scripts/copy_zip_to_website.py
```

This produces `website/downloads/Inkscape-AI.zip`, which the site's Download
buttons link to directly.

## Deploying

The site is 100% static and portable. Whichever host you pick (Netlify,
Vercel, GitHub Pages, S3, etc.):

1. Run the two build commands above from the repo root.
2. Publish/upload the `website/` folder as-is.

If your host supports a build command, you can chain both steps into one:
`python scripts/build_extension_zip.py && python scripts/copy_zip_to_website.py`,
with the publish directory set to `website`.

## Adding real screenshots/video later

Every placeholder in `index.html` (the dashed boxes) has an HTML comment
directly beneath it showing the exact `<img>`/`<video>` markup to drop in and
which reserved filename to use, e.g.:

- `assets/img/screenshots/hero-review.png`
- `assets/img/screenshots/install-windows-success.png`
- `assets/img/screenshots/install-mac-success.png`
- `assets/img/screenshots/install-linux-success.png`
- `assets/video/usage-demo.mp4` (+ `.webm`, + `assets/img/screenshots/usage-poster.png` poster)

Drop the file into the matching folder, delete the placeholder `<div class="media-frame">`,
and uncomment the real markup below it — no other changes needed.

## Enabling Google Analytics later

Open `js/analytics.js` and fill in `GA_MEASUREMENT_ID` with your GA4
measurement ID (e.g. `"G-XXXXXXXXXX"`). The script is inert (loads, fires no
network requests) until that constant is set — no HTML changes needed.
