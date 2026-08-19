#!/bin/bash
set -e

echo "Dev Container Entrypoint"

ENV_FILE="/workspaces/app/.env"
if [ -f "$ENV_FILE" ]; then
  echo "Loading environment variables from .env"
  source "$ENV_FILE"
fi

cd /workspaces/app

# Install dependencies once before starting the dev server.
if [ ! -d "node_modules/astro" ]; then
  echo "Installing dependencies with Yarn"
  YARN_ENABLE_TELEMETRY=0 CHILD_CONCURRENCY=2 yarn install
fi

if [ $# -gt 0 ]; then
  echo "Executing: $@"
  exec "$@"
else
  echo "Starting interactive shell..."
  exec /bin/bash
fi
