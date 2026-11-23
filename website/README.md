# StitchBase website

Static, plain HTML/CSS/JS download & marketing site for the StitchBase
Inkscape extension. No build step, no dependencies — just files you can open
directly or deploy to any static host.

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

This produces `website/downloads/StitchBase.zip`, which the site's Download
buttons link to directly.

## Deploying

The site is 100% static and portable. Whichever host you pick (Netlify,
Vercel, GitHub Pages, S3, etc.):

1. Run the two build commands above from the repo root.
2. Publish/upload the `website/` folder as-is.

If your host supports a build command, you can chain both steps into one:
`python scripts/build_extension_zip.py && python scripts/copy_zip_to_website.py`,
with the publish directory set to `website`.

## Real screenshots/video

The hero screenshot and the two videos are live:

- `assets/img/screenshots/hero-review.png` — hero screenshot (design preview +
  preflight findings + chat), shown in `.screenshot-frame`.
- `assets/video/demo.mp4` — full workflow walkthrough, embedded in the
  "How it works" section (`.video-frame`).
- `assets/video/installation.mp4` — installer walkthrough, embedded above the
  OS install tabs (`.video-frame.install-video`).

The per-OS "install success" screenshot placeholders (Windows/macOS/Linux)
were removed — there are no screenshots for those, and the installation video
above the tabs already covers that visually. If real per-OS screenshots show
up later, add a `.screenshot-frame` (see hero markup) inside each `.tabpanel`
and restore the two-column `.tabpanel` grid in `styles.css`.

## Enabling Google Analytics later

Open `js/analytics.js` and fill in `GA_MEASUREMENT_ID` with your GA4
measurement ID (e.g. `"G-XXXXXXXXXX"`). The script is inert (loads, fires no
network requests) until that constant is set — no HTML changes needed.
