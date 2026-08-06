# Deployment — EC2 (inkscape-ai-beta)

## Server

| | |
|---|---|
| Instance | `i-0ea8ad31b02d84884` ("inkscape-ai-beta"), ap-south-1, t3.small |
| Public IP | `13.234.128.12` |
| Public DNS | `ec2-13-234-128-12.ap-south-1.compute.amazonaws.com` |
| Domain | `stitchbase.duckdns.org` → points at the public IP, HTTPS via Caddy |
| OS | Amazon Linux 2023 → SSH user is `ec2-user` |
| SSH key | `inkscape-ai-beta.pem` (repo root) |

Caddy runs on the host (its own container, `caddy`) and reverse-proxies
`stitchbase.duckdns.org` → `127.0.0.1:8000`, where the `inkscape-ai` Docker
container (built from image `inkscape-ai-beta`) listens. Code + `.env` live in
`/home/ec2-user/BE` on the box. This deploy only touches the `inkscape-ai`
container — Caddy's config and TLS certs are untouched.

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
   rollback point) and starts the new one under the original name/port/volumes.
5. Polls `/health` for ~20s. If it doesn't come up healthy, it automatically
   rolls back to `inkscape-ai-prev`.

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
