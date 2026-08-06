# Inkscape AI — Admin Dashboard

A private, single-file dashboard to explore the anonymous user-journey analytics
(visitors, sessions, SVGs, chats, timings, rule-engine findings, errors) captured
by the backend and stored in Supabase.

This folder is for **you only**. It is not served to end users.

## Setup (one time)

1. Open `admin/index.html` in your browser (double-click the file).

2. In the "Connect to your backend" dialog, enter:
   - **Backend base URL** — e.g. `https://stitchbase.duckdns.org` (or
     `http://localhost:8000` when running locally)

   This is saved in your browser's localStorage only. Use **Settings** to change it.

## What you can see

- **Overview** — totals (visitors, sessions, messages), sessions over the last
  14 days, rule-decision mix, top issues detected, and session type.
- **Visitors** — every anonymous visitor (cookie id), with session/message
  counts, first/last seen, IP, and device. Click a row to see their sessions.
- **Sessions** — searchable/filterable list. Click a session to open a detail
  panel with metadata, an **inline SVG preview**, the rule-engine findings, and
  the **full chat transcript** (with AI latency per reply).
- **Journey** — a timeline of milestone events (created, opened, uploaded,
  replaced, chat error, deleted). Click an event to jump to its session.

## Security notes

- **The admin API has no authentication.** Anyone who knows (or guesses) your
  backend URL can read all analytics at `/admin/api/*` — visitor IPs, full
  chat transcripts, full SVG designs. Don't share the backend URL, and treat
  it as effectively public if it leaks.
- The admin API also allows any origin (so this local file can call it from
  `file://`).
- If you want this locked down again later, add back a token check or an IP
  allowlist in `BE/app/api/v1/admin.py` / at the reverse proxy (Caddy).
