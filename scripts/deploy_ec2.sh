#!/usr/bin/env bash
# Deploy BE/ to the EC2 box over SSH using the .pem key.
# Run from the repo root with Git Bash / WSL / any bash that has ssh, scp, tar.
#
#   ./scripts/deploy_ec2.sh
#
set -euo pipefail

# ---- config: verify these match the server before first run -------------
EC2_HOST="13.234.128.12"
SSH_USER="ec2-user"                       # Amazon Linux 2023 default user
PEM_KEY="./inkscape-ai-beta.pem"
REMOTE_APP_DIR="/home/ec2-user/stitchbase-be"   # where code lives on the box
CONTAINER_NAME="stitchbase-be"
HOST_PORT="8000"                          # Caddy proxies to this port
# ---------------------------------------------------------------------------

chmod 600 "$PEM_KEY"
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

# Keep the old container around (stopped) as an instant rollback point.
if docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  docker rm -f "${CONTAINER_NAME}-prev" >/dev/null 2>&1 || true
  docker rename "$CONTAINER_NAME" "${CONTAINER_NAME}-prev" || true
  docker stop "${CONTAINER_NAME}-prev" >/dev/null 2>&1 || true
fi

docker run -d \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  -p 127.0.0.1:${HOST_PORT}:8000 \
  --env-file "$REMOTE_APP_DIR/.env" \
  -v "$REMOTE_APP_DIR/data:/app/data" \
  "${CONTAINER_NAME}:latest"

echo "Waiting for health check..."
for i in \$(seq 1 10); do
  if curl -fsS "http://127.0.0.1:${HOST_PORT}/health" >/dev/null 2>&1; then
    echo "Healthy."
    docker rm -f "${CONTAINER_NAME}-prev" >/dev/null 2>&1 || true
    exit 0
  fi
  sleep 2
done

echo "Health check FAILED — rolling back to previous container."
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker rename "${CONTAINER_NAME}-prev" "$CONTAINER_NAME" || true
docker start "$CONTAINER_NAME" || true
exit 1
REMOTE

echo "==> Done. Live at https://stitchbase.duckdns.org/health"
