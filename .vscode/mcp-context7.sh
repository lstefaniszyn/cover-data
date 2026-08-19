#!/bin/bash
# MCP Context7 wrapper script
# This script runs the Context7 MCP server via Docker

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

# Get API key from argument or environment variable
# If argument is the literal string '${CONTEXT7_API_KEY}', ignore it
if [ "$1" = '${CONTEXT7_API_KEY}' ] || [ -z "$1" ]; then
    API_KEY="${CONTEXT7_API_KEY}"
else
    API_KEY="$1"
fi

if [ -z "${API_KEY}" ]; then
    echo "Error: CONTEXT7_API_KEY not provided" >&2
    echo "Usage: $0 <api-key>" >&2
    echo "Or set CONTEXT7_API_KEY in your .env file" >&2
    exit 1
fi

# Validate API key format
if [[ ! "${API_KEY}" =~ ^ctx7sk- ]]; then
    echo "Error: Invalid API key format. API key must start with 'ctx7sk-'" >&2
    exit 1
fi

echo "Starting Context7 MCP server via npx..." >&2

# Run the Context7 MCP server using npx with the correct package name
# The API key is passed via environment variable
export CONTEXT7_API_KEY="${API_KEY}"
exec npx -y @upstash/context7-mcp
