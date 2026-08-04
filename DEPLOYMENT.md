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

Caddy runs on the host and reverse-proxies `stitchbase.duckdns.org` → `127.0.0.1:8000`,
where the `stitchbase-be` Docker container listens. This deploy only touches that
container — Caddy's config and TLS certs are untouched.

## Deploy

```bash
./scripts/deploy_ec2.sh
```

What it does:
1. Tars `BE/` locally (skips `.venv`, `data/`, `.git`, `.env`, caches).
2. `scp`s it to `/home/ec2-user/stitchbase-be` on the server.
3. SSHs in, `docker build`s a fresh image.
4. Renames the running container to `stitchbase-be-prev` (stopped, kept as a
   rollback point) and starts the new one under the original name/port/volumes.
5. Polls `/health` for ~20s. If it doesn't come up healthy, it automatically
   rolls back to `stitchbase-be-prev`.

The server's `.env` (API keys, `DATABASE_URL`, etc.) and `data/` (SQLite DB,
uploaded SVGs, chroma index) are **never overwritten** — they're excluded from
the upload and the container mounts `data/` as a volume.

**First run only** — the config block at the top of `scripts/deploy_ec2.sh`
(`REMOTE_APP_DIR`, `CONTAINER_NAME`, `HOST_PORT`) assumes this is the first
automated deploy. If the server already has a differently-named container or
directory from earlier manual deploys, SSH in once and check before running:

```bash
ssh -i inkscape-ai-beta.pem ec2-user@13.234.128.12 "docker ps -a"
```

Adjust the variables to match if they differ.

## Rollback (manual)

If a bad deploy needs reverting after the fact:

```bash
ssh -i inkscape-ai-beta.pem ec2-user@13.234.128.12 \
  'docker rm -f stitchbase-be; docker rename stitchbase-be-prev stitchbase-be; docker start stitchbase-be'
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
