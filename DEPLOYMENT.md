# Deployment — EC2 (inkscape-ai-beta)

## Server

| | |
|---|---|
| Instance | `i-0ea8ad31b02d84884` ("inkscape-ai-beta"), ap-south-1, t3.small |
| Public IP | `13.234.128.12` |
| Public DNS | `ec2-13-234-128-12.ap-south-1.compute.amazonaws.com` |
| Domain | `app.stitchbase.online` → points at the public IP, HTTPS via Caddy (also still reachable at the legacy `stitchbase.duckdns.org`) |
| OS | Amazon Linux 2023 → SSH user is `ec2-user` |
| SSH key | `inkscape-ai-beta.pem` (repo root) |

Caddy runs on the host (its own container, `caddy`) and reverse-proxies
`app.stitchbase.online` (and `stitchbase.duckdns.org`) → the `inkscape-ai`
container **by Docker DNS name** (`inkscape-ai:8000`), not by host port — both
containers share a user-defined Docker network called **`web`**. (The
container also separately publishes `127.0.0.1:8000` on the host, which is why
a direct `curl 127.0.0.1:8000/health` on the box can look healthy even when
Caddy can't reach it — see incident below.)
Code + `.env` live in `/home/ec2-user/BE` on the box. This deploy only touches
the `inkscape-ai` container — Caddy's config and TLS certs are untouched.

Caddy also separately serves the static marketing site (`website/`, deployed
manually to `/home/ec2-user/website` on the box, mounted read-only into the
`caddy` container at `/srv/website`) at `stitchbase.online` and
`www.stitchbase.online`. See `/home/ec2-user/caddy/Caddyfile` on the server for
the full routing — it's not tracked in this repo.

2026-08-05: added `app.stitchbase.online` (backend) and
`stitchbase.online`/`www.stitchbase.online` (marketing site) as a second
domain — the `caddy` container was recreated (not just reloaded, since the
`/srv/website` bind mount required it) with an extra volume for the site
files. `caddy_data`/`caddy_config` named volumes were preserved across the
recreation, so the existing `stitchbase.duckdns.org` cert was untouched — see
`git log` on this file for the exact commands run.

## Deploy

```bash
./scripts/deploy_ec2.sh
```

What it does:
1. Tars `BE/` locally (skips `.venv`, `data/`, `.git`, `.env`, caches).
2. `scp`s it into `/home/ec2-user/BE` on the server, extracting on top of the
   existing directory (so `.env` and `data/` there are left untouched — they're
   not in the uploaded archive).
3. SSHs in, `docker build`s a fresh image (`inkscape-ai:latest`).
4. Renames the running container to `inkscape-ai-prev` (stopped, kept as a
   rollback point), captures the Docker network(s) it was on, and starts the
   new one on the **same network(s)** plus the original port/volumes.
5. Polls `/health` directly on the container, **then polls
   `https://stitchbase.duckdns.org/health` end-to-end through Caddy** — the
   actual public path. Either check failing triggers an automatic rollback to
   `inkscape-ai-prev`.

### ⚠️ Incident (2026-08-05): 502 after deploy, container network dropped

An early version of this script recreated the container with a plain
`docker run` (no `--network`), which put it on the isolated default `bridge`
network instead of the `web` network Caddy uses to reach it by DNS name. The
container itself was perfectly healthy (`curl 127.0.0.1:8000/health` → 200 on
the box), so the script's health check passed — but Caddy got
`dial tcp: lookup inkscape-ai on 127.0.0.11:53: no such host` and the public
site 502'd until manually fixed with `docker network connect web inkscape-ai`.
Fixed in the script two ways: it now preserves the container's original
network(s) across redeploys, and the health check goes through
`stitchbase.duckdns.org` (the real public path) rather than only the direct
container port — so a network regression like this fails the deploy and
auto-rolls-back instead of shipping silently.

The server's `.env` (API keys, `DATABASE_URL`, etc.) and `data/` (SQLite DB,
uploaded SVGs, chroma index) are **never overwritten** — they're excluded from
the upload and the container mounts `data/` as a volume.

Confirmed once via `docker ps -a` on 2026-08-04 — real container is `inkscape-ai`,
real code path is `/home/ec2-user/BE`. The script's config block already
reflects this; only revisit it if the server setup changes.

## Rollback (manual)

If a bad deploy needs reverting after the fact:

```bash
ssh -i inkscape-ai-beta.pem ec2-user@13.234.128.12 \
  'docker rm -f inkscape-ai; docker rename inkscape-ai-prev inkscape-ai; docker start inkscape-ai'
```

## ⚠️ Open security issue

`inkscape-ai-beta.pem` (the private SSH key used above) is **committed and
tracked in this git repo** — it's not in `.gitignore` and shows up in
`git ls-files`. Anyone with read access to this repo (or its GitHub remote,
`hemanthkumar7806/embroidery-ext`) can SSH into the production box with it.

Recommended fix, when convenient:
1. Generate a new key pair, add the new public key to the EC2 instance's
   `~/.ssh/authorized_keys`, remove the old one.
2. `git rm --cached inkscape-ai-beta.pem`, add `*.pem` to `.gitignore`.
3. Since the key is in prior commits too, it stays recoverable from git
   history even after removal — treat it as already exposed and rotate it
   rather than relying on history rewrite.
