# Inkscape AI — Admin Dashboard

A private, single-file dashboard to explore the anonymous user-journey analytics
(visitors, sessions, SVGs, chats, timings, rule-engine findings, errors) captured
by the backend and stored in Supabase.

This folder is for **you only**. It is not served to end users.

## Setup (one time)

1. On the backend, set a secret admin token in the environment (`.env`):

   ```
   ADMIN_TOKEN=choose-a-long-random-string
   ```

   Restart / redeploy the backend so it picks up the value. If `ADMIN_TOKEN`
   is empty, the admin API stays disabled (returns 503).

2. Open `admin/index.html` in your browser (double-click the file).

3. In the "Connect to your backend" dialog, enter:
   - **Backend base URL** — e.g. `https://stitchbase.duckdns.org` (or
     `http://localhost:8000` when running locally)
   - **Admin token** — the same value as `ADMIN_TOKEN`

   These are saved in your browser's localStorage only. Use **Settings** to change them.

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

- The admin API is protected by the `X-Admin-Token` header; keep the token
  secret. Anyone with the token + URL can read all analytics.
- The admin API allows any origin (so this local file can call it), but every
  data endpoint still requires the token. Only the unauthenticated `/ping`
  endpoint is public, and it only reports whether admin is enabled.
- For extra safety in production you can additionally restrict `/admin/api` at
  the reverse proxy (Caddy) to your IP.
