#!/bin/bash
# MCP PostgreSQL wrapper script using @executeautomation/database-server
# This script runs the PostgreSQL MCP server via npx (no Docker required)

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

# Get database name from argument
DATABASE_NAME="${1:-${POSTGRES_DB:-app}}"

# Use environment variables with defaults
POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"

echo "Starting PostgreSQL MCP server for database: ${DATABASE_NAME}" >&2

# Run the PostgreSQL MCP server using npx
# Using @executeautomation/database-server package
exec npx -y @executeautomation/database-server \
    --postgresql \
    --host "${POSTGRES_HOST}" \
    --database "${DATABASE_NAME}" \
    --user "${POSTGRES_USER}" \
    --password "${POSTGRES_PASSWORD}" \
    --port "${POSTGRES_PORT}"
CONNECTION_STRING_RAW="$1"
if [ -z "$CONNECTION_STRING_RAW" ]; then
    echo "Usage: $0 <connection-string>" >&2
    exit 1
fi

# If POSTGRES_* vars are not set, try to parse them from the provided connection string.
# Use python3's urlparse when available for robust parsing; fall back to sed-based parsing.
if [ -z "${POSTGRES_USER}${POSTGRES_PASSWORD}${POSTGRES_HOST}${POSTGRES_PORT}${POSTGRES_DB}" ]; then
    if command -v python3 >/dev/null 2>&1; then
        parsed=$(python3 - <<PY
import sys
from urllib.parse import urlparse
s = sys.argv[1]
u = urlparse(s)
user = u.username or ''
pw = u.password or ''
host = u.hostname or ''
port = str(u.port) if u.port else ''
db = u.path.lstrip('/') if u.path else ''
print('|'.join([user,pw,host,port,db]))
PY
 "$CONNECTION_STRING_RAW") || parsed="||||"
    else
        # crude sed extraction: postgresql://user:pass@host:port/db
        parsed=$(echo "$CONNECTION_STRING_RAW" | sed -E 's#postgresql://([^:]+):([^@]+)@([^:]+):?([0-9]*)(/.*)?#\1|\2|\3|\4|\5#')
    fi
    IFS='|' read -r p_user p_pass p_host p_port p_db <<< "$parsed"
    : ${POSTGRES_USER:=$p_user}
    : ${POSTGRES_PASSWORD:=$p_pass}
    : ${POSTGRES_HOST:=$p_host}
    : ${POSTGRES_PORT:=$p_port}
    : ${POSTGRES_DB:=${p_db#/}}
fi

# Expand environment variables in the connection string (if any are present)
CONNECTION_STRING=$(eval echo "$CONNECTION_STRING_RAW")

# Now resolve the database host IP
DB_IP=""

# 1) literal IPv4
if [[ "${POSTGRES_HOST}" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    DB_IP="${POSTGRES_HOST}"
fi

# 2) try getent (system DNS/hosts)
if [ -z "${DB_IP}" ]; then
    DB_IP=$(getent hosts "${POSTGRES_HOST}" | awk '{print $1}')
fi

# 3) try docker (container name or network alias)
if [ -z "${DB_IP}" ] && command -v docker >/dev/null 2>&1; then
    # Try to find a container whose name matches POSTGRES_HOST
    CID=$(docker ps -a --filter "name=^/${POSTGRES_HOST}$" --format '{{.ID}}' | head -n1)
    if [ -z "${CID}" ]; then
        CID=$(docker ps -a --filter "name=${POSTGRES_HOST}" --format '{{.ID}}' | head -n1)
    fi

    if [ -n "${CID}" ]; then
        DB_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${CID}" 2>/dev/null)
    fi

    # If still not found, scan running containers for network aliases matching POSTGRES_HOST
    if [ -z "${DB_IP}" ]; then
        for cid in $(docker ps -q); do
            aliases=$(docker inspect -f '{{range $net,$conf := .NetworkSettings.Networks}}{{range $i,$a := $conf.Aliases}}{{$a}}{{"\n"}}{{end}}{{end}}' "$cid" 2>/dev/null || true)
            if echo "$aliases" | grep -xq "${POSTGRES_HOST}"; then
                DB_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$cid" 2>/dev/null)
                break
            fi
        done
    fi
fi

if [ -z "$DB_IP" ]; then
    echo "Error: Cannot resolve '${POSTGRES_HOST}' hostname to an IP" >&2
    exit 1
fi

# Prepare an updated connection string. By default we replace the hostname
# with the resolved DB_IP, but if the host's port is reachable and we're on
# Linux, prefer running the helper with host networking and use 'localhost'
# in the connection string (this is more reliable in devcontainers).
prefix="${CONNECTION_STRING%@*}"
suffix="${CONNECTION_STRING##*@}"
# Remove the host from the suffix (keep leading ':' or '/' and the rest)
rest=$(echo "$suffix" | sed -E 's#^[^:/]+##')

# If we found a Docker container CID earlier, try to get its network name and
# run the helper attached to that network — containers on the same Docker
# network can reach each other by hostname, which is the cleanest solution.
DOCKER_NET=""
if [ -n "${CID}" ] && command -v docker >/dev/null 2>&1; then
    DOCKER_NET=$(docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}' "${CID}" 2>/dev/null | awk '{print $1}') || true
    if [ -n "${DOCKER_NET}" ]; then
        echo "Detected DB container '${CID}' on Docker network: ${DOCKER_NET}"
        echo "Probing connectivity to ${POSTGRES_HOST}:${POSTGRES_PORT} via Docker network '${DOCKER_NET}'..."
        if docker run --rm --network "${DOCKER_NET}" -e PGPASSWORD="${POSTGRES_PASSWORD}" postgres:16 pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" >/dev/null 2>&1; then
            echo "Probe successful on Docker network '${DOCKER_NET}'. Starting mcp/postgres attached to that network."
            # Use the original connection string (host as provided) so hostname resolves inside the network
            exec docker run -i --rm --network "${DOCKER_NET}" mcp/postgres "${CONNECTION_STRING}"
        else
            echo "Probe on Docker network '${DOCKER_NET}' failed; will continue with host/add-host attempts." >&2
        fi
    fi
fi

CONNECTION_STRING_IP="${prefix}@localhost${rest}"
echo >&2 "Attempting host-network probe first; Connection String (with localhost): $CONNECTION_STRING_IP"
echo >&2 "Probing connectivity to localhost:${POSTGRES_PORT} from a container via --network host..."
if docker run --rm --network host -e PGPASSWORD="${POSTGRES_PASSWORD}" postgres:16 pg_isready -h localhost -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" >/dev/null 2>&1; then
    echo >&2 "Host-network probe successful. Starting mcp/postgres with --network host"
    exec docker run -i --rm --network host mcp/postgres "${CONNECTION_STRING_IP}"
else
    echo >&2 "Host-network probe failed. Falling back to container network using --add-host"

    # Fallback: try connecting via container network using --add-host
    CONNECTION_STRING_IP="${prefix}@${DB_IP}${rest}"
    echo >&2 "Using container network; Connection String (with DB_IP): $CONNECTION_STRING_IP"
    echo >&2 "Probing connectivity to ${DB_IP}:${POSTGRES_PORT} from a container using --add-host..."
    if docker run --rm --add-host="${POSTGRES_HOST}:${DB_IP}" -e PGPASSWORD="${POSTGRES_PASSWORD}" postgres:16 pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" >/dev/null 2>&1; then
        echo >&2 "Probe successful. Starting mcp/postgres with --add-host=${POSTGRES_HOST}:${DB_IP}"
        exec docker run -i --rm --add-host="${POSTGRES_HOST}:${DB_IP}" mcp/postgres "$CONNECTION_STRING_IP"
    else
        echo >&2 "Connectivity probe failed: cannot reach ${DB_IP}:${POSTGRES_PORT} from a container."
        echo >&2 "Diagnostic: local getent hosts ${POSTGRES_HOST} output:"
        getent hosts "${POSTGRES_HOST}" 2>/dev/null >&2 || true
        echo >&2 "Diagnostic: resolved DB_IP=${DB_IP}"
        echo >&2 "You can try running the following command locally to debug:"
        echo >&2 "  docker run --rm --add-host=\"${POSTGRES_HOST}:${DB_IP}\" -e PGPASSWORD=... postgres:16 pg_isready -h \"${POSTGRES_HOST}\" -p \"${POSTGRES_PORT}\" -U \"${POSTGRES_USER}\""
        exit 1
    fi
fi
