#!/bin/bash
# MCP Material UI wrapper script
# This script runs the Material UI MCP server via npx

# Load environment variables from .env file if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

if [ -f "${ENV_FILE}" ]; then
    echo "Loading environment from ${ENV_FILE}" >&2
    # Export variables from .env file
    set -a
    source "${ENV_FILE}"
    set +a
fi

echo "Starting Material UI MCP server via npx..." >&2

# Run the Material UI MCP server using npx (official method from MUI docs)
# Uses the latest version of @mui/mcp package
# Proxy settings will be inherited from environment
exec npx -y @mui/mcp@latest
