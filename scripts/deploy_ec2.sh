#!/usr/bin/env bash
# Deploy BE/ to the EC2 box over SSH using the .pem key.
# Run from the repo root with Git Bash / WSL / any bash that has ssh, scp, tar.
#
#   ./scripts/deploy_ec2.sh
#
set -euo pipefail

# ---- config: matches the actual running setup (confirmed via `docker ps -a`) --
EC2_HOST="13.234.128.12"
SSH_USER="ec2-user"                       # Amazon Linux 2023 default user
PEM_KEY="./inkscape-ai-beta.pem"
REMOTE_APP_DIR="/home/ec2-user/BE"        # existing code + .env live here
CONTAINER_NAME="inkscape-ai"              # existing container Caddy proxies to
HOST_PORT="8000"                          # Caddy proxies to this port
# ---------------------------------------------------------------------------

# ssh on Windows checks the NTFS ACL, not POSIX mode bits — chmod doesn't apply there.
if command -v icacls >/dev/null 2>&1; then
  icacls "$PEM_KEY" /inheritance:r >/dev/null
  icacls "$PEM_KEY" /grant:r "$(whoami):R" >/dev/null
else
  chmod 600 "$PEM_KEY"
fi
SSH="ssh -i $PEM_KEY -o StrictHostKeyChecking=accept-new $SSH_USER@$EC2_HOST"
SCP="scp -i $PEM_KEY -o StrictHostKeyChecking=accept-new"

echo "==> Packing BE/ (excluding .venv, data, .git, __pycache__, .env)"
TARBALL="$(mktemp -t be-deploy-XXXX).tar.gz"
tar -czf "$TARBALL" -C BE \
  --exclude='.venv' \
  --exclude='data' \
  --exclude='.git' \
  --exclude='.github' \
  --exclude='__pycache__' \
  --exclude='.env' \
  --exclude='.pytest_cache' \
  .

echo "==> Uploading code to $EC2_HOST:$REMOTE_APP_DIR"
$SSH "mkdir -p $REMOTE_APP_DIR"
$SCP "$TARBALL" "$SSH_USER@$EC2_HOST:/tmp/be-deploy.tar.gz"
$SSH "tar -xzf /tmp/be-deploy.tar.gz -C $REMOTE_APP_DIR && rm /tmp/be-deploy.tar.gz"
rm "$TARBALL"

echo "==> Building image and restarting container on the server"
$SSH bash -s <<REMOTE
set -euo pipefail
cd "$REMOTE_APP_DIR"

docker build -t ${CONTAINER_NAME}:latest .

# Capture the container's Docker network(s) BEFORE recreating it — Caddy reaches this
# container by Docker DNS name (e.g. "inkscape-ai:8000"), which only resolves within a
# shared user-defined network. A plain \`docker run\` without --network lands on the
# isolated default bridge network and silently breaks Caddy's reverse_proxy (502,
# "no such host") even though the container itself is perfectly healthy. Losing this once
# is exactly what happened; this is deploy_ec2.sh preserving it automatically from now on.
PREV_NETWORKS=""
if docker container inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  PREV_NETWORKS="\$(docker inspect "$CONTAINER_NAME" --format '{{range \$k,\$v := .NetworkSettings.Networks}}{{\$k}} {{end}}')"
  docker rm -f "${CONTAINER_NAME}-prev" >/dev/null 2>&1 || true
  docker rename "$CONTAINER_NAME" "${CONTAINER_NAME}-prev" || true
  docker stop "${CONTAINER_NAME}-prev" >/dev/null 2>&1 || true
fi

NETWORK_FLAG=""
EXTRA_NETWORKS=""
first=1
for net in \$PREV_NETWORKS; do
  if [ "\$first" = 1 ]; then
    NETWORK_FLAG="--network \$net"
    first=0
  else
    EXTRA_NETWORKS="\$EXTRA_NETWORKS \$net"
  fi
done

docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  \$NETWORK_FLAG \
  -p 127.0.0.1:${HOST_PORT}:8000 \
  --env-file "$REMOTE_APP_DIR/.env" \
  -v "$REMOTE_APP_DIR/data:/app/data" \
  "${CONTAINER_NAME}:latest"

for net in \$EXTRA_NETWORKS; do
  docker network connect "\$net" "$CONTAINER_NAME" || true
done

rollback() {
  echo "\$1 — rolling back to previous container."
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  docker rename "${CONTAINER_NAME}-prev" "$CONTAINER_NAME" || true
  docker start "$CONTAINER_NAME" || true
  exit 1
}

echo "Waiting for container health check (direct, bypasses Caddy)..."
container_ok=0
for i in \$(seq 1 10); do
  if curl -fsS "http://127.0.0.1:${HOST_PORT}/health" >/dev/null 2>&1; then
    container_ok=1
    break
  fi
  sleep 2
done
[ "\$container_ok" = 1 ] || rollback "Container health check FAILED"

echo "Waiting for end-to-end health check through Caddy (the real public path)..."
edge_ok=0
for i in \$(seq 1 10); do
  if curl -fsS "https://app.stitchbase.online/health" >/dev/null 2>&1; then
    edge_ok=1
    break
  fi
  sleep 2
done
[ "\$edge_ok" = 1 ] || rollback "End-to-end health check through Caddy FAILED (container is up but unreachable via Caddy — network misconfiguration?)"

echo "Healthy end-to-end."
docker rm -f "${CONTAINER_NAME}-prev" >/dev/null 2>&1 || true
REMOTE

echo "==> Done. Live at https://app.stitchbase.online/health"
