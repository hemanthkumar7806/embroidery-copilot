#!/bin/bash
set -e

if [ -f ".env" ]; then
  echo "Loading .env"
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

exec "$@"
