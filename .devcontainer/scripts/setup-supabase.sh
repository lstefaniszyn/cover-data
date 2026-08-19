#!/bin/bash
# Starts the local Supabase stack and writes credentials to .env and .dev.vars.
# Runs automatically via postStartCommand on every devcontainer start.
#
# Health-check strategy (avoids Docker-outside-of-Docker container inspection):
#   - Port forwards: socat from 127.0.0.1 → docker-host-gateway:port
#   - Host IP: discovered from `docker inspect supabase_kong_<id>` + `ip route`
#   - Credentials: JWT signed from JWT_SECRET in the db container env
#   - Readiness: direct HTTP probe on Kong, no `npx supabase status`

set -e

WORKDIR="/workspaces/app"
cd "$WORKDIR"

PROJECT_ID=$(awk -F '"' '/^project_id = / {print $2}' "$WORKDIR/supabase/config.toml")
PROJECT_ID=${PROJECT_ID:-$(basename "$WORKDIR")}
SUPABASE_PORTS=(54320 54321 54322 54323 54324)
API_PORT=54321

# ── Host discovery ────────────────────────────────────────────────────────────
# Derive the reachable host IP from the Kong container's port bindings.
# If Kong binds to 0.0.0.0 (the common case), fall back to the default-route
# gateway — that is the Docker host as seen from inside this container.
discover_supabase_host() {
    local container="supabase_kong_${PROJECT_ID}"
    local host_ip

    host_ip=$(docker inspect "$container" \
        --format '{{range $p, $b := .NetworkSettings.Ports}}{{if $b}}{{(index $b 0).HostIp}}{{end}}{{end}}' \
        2>/dev/null | grep -Ev '^$|^::$|^0\.0\.0\.0$' | head -1 || true)

    if [ -z "$host_ip" ]; then
        host_ip=$(ip route | awk '/^default via/ {print $3; exit}')
    fi

    echo "$host_ip"
}

# ── Zombie-aware PID check ───────────────────────────────────────────────────
# `kill -0` succeeds for zombie processes (they still have a PID slot).
# Read the state field from /proc to distinguish live from zombie.
pid_is_alive() {
    local pid="$1"
    kill -0 "$pid" 2>/dev/null || return 1
    local state
    state=$(awk '{print $3}' "/proc/${pid}/stat" 2>/dev/null || echo "")
    [ "$state" != "Z" ]
}

# ── Port-forward management ──────────────────────────────────────────────────
has_running_supabase_stack() {
    docker ps --format '{{.Names}}' | grep -Eq "^supabase_(kong|db|rest)_${PROJECT_ID}$"
}

is_port_listening() {
    timeout 1 bash -c ":</dev/tcp/127.0.0.1/${1}" >/dev/null 2>&1
}

stop_supabase_port_forwards() {
    local port pid_file pid
    for port in "${SUPABASE_PORTS[@]}"; do
        pid_file="/tmp/supabase-${PROJECT_ID}-${port}.pid"
        [ -f "$pid_file" ] || continue
        pid=$(cat "$pid_file")
        if [ -n "$pid" ] && pid_is_alive "$pid"; then
            kill "$pid" 2>/dev/null || true
        fi
        rm -f "$pid_file"
    done
}

start_supabase_port_forwards() {
    local host="$1"
    local port pid_file pid

    if ! command -v socat >/dev/null 2>&1; then
        echo ""
        echo "❌ socat is not available inside the devcontainer."
        echo "   Rebuild the devcontainer so the image includes socat."
        exit 1
    fi

    for port in "${SUPABASE_PORTS[@]}"; do
        pid_file="/tmp/supabase-${PROJECT_ID}-${port}.pid"

        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            if [ -n "$pid" ] && pid_is_alive "$pid"; then
                continue  # already forwarding
            fi
            rm -f "$pid_file"
        fi

        is_port_listening "$port" && continue

        socat "TCP-LISTEN:${port},fork,reuseaddr,bind=127.0.0.1" \
              "TCP:${host}:${port}" \
              >"/tmp/supabase-${PROJECT_ID}-${port}.log" 2>&1 &
        echo "$!" > "$pid_file"
    done
}

start_deferred_supabase_port_forwards() {
    local host="$1"
    (
        for _ in $(seq 1 120); do
            if has_running_supabase_stack; then
                start_supabase_port_forwards "$host"
                exit 0
            fi
            sleep 1
        done
    ) &
    FORWARD_BOOTSTRAP_PID=$!
}

connect_app_to_supabase_network() {
    local network="supabase_network_${PROJECT_ID}"
    local app_container="${HOSTNAME:-}"

    [ -n "$app_container" ] || return 1
    docker network inspect "$network" >/dev/null 2>&1 || return 1

    if docker network inspect "$network" --format '{{json .Containers}}' | grep -Fq "$app_container"; then
        return 0
    fi

    docker network connect "$network" "$app_container" 2>/dev/null || true
}

supabase_api_url() {
    if connect_app_to_supabase_network; then
        echo "http://supabase_kong_${PROJECT_ID}:8000"
    else
        echo "http://127.0.0.1:${API_PORT}"
    fi
}

# ── Credential derivation ────────────────────────────────────────────────────
# Read JWT_SECRET from the db container and generate the standard anon JWT.
# Falls back to empty string on error (caller must check).
derive_anon_key() {
    local jwt_secret
    jwt_secret=$(docker exec "supabase_db_${PROJECT_ID}" env 2>/dev/null \
        | grep '^JWT_SECRET=' | cut -d= -f2-)
    [ -z "$jwt_secret" ] && return 1

    python3 - "$jwt_secret" <<'PYEOF'
import sys, base64, json, hmac, hashlib

def b64url(data):
    if isinstance(data, str): data = data.encode()
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

secret = sys.argv[1]
header  = b64url(json.dumps({"alg":"HS256","typ":"JWT"}, separators=(',',':')))
payload = b64url(json.dumps({"role":"anon","iss":"supabase","iat":1441827000,"exp":1809843200}, separators=(',',':')))
sig     = b64url(hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
print(f"{header}.{payload}.{sig}")
PYEOF
}

# ── Health check ─────────────────────────────────────────────────────────────
# Probe Kong directly over HTTP — no Docker container inspection needed.
wait_for_supabase_api() {
    local host="$1"
    local attempts=20
    local code

    for i in $(seq 1 "$attempts"); do
        code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 \
            "http://${host}:${API_PORT}/" 2>/dev/null || echo "000")
        if [ "$code" != "000" ]; then
            return 0
        fi
        echo "   Kong not ready (${i}/${attempts}); waiting 3s..."
        sleep 3
    done
    return 1
}

# ── Env file writer ──────────────────────────────────────────────────────────
write_env_vars() {
    local api_url="$1"
    local anon_key="$2"

    [ -f "$WORKDIR/.env" ]      || cp "$WORKDIR/.env.example"      "$WORKDIR/.env"
    [ -f "$WORKDIR/.dev.vars" ] || cp "$WORKDIR/.dev.vars.example" "$WORKDIR/.dev.vars"

    sed -i "s|SUPABASE_URL=.*|SUPABASE_URL=${api_url}|"  "$WORKDIR/.env"
    sed -i "s|SUPABASE_KEY=.*|SUPABASE_KEY=${anon_key}|" "$WORKDIR/.env"
    sed -i "s|SUPABASE_URL=.*|SUPABASE_URL=${api_url}|"  "$WORKDIR/.dev.vars"
    sed -i "s|SUPABASE_KEY=.*|SUPABASE_KEY=${anon_key}|" "$WORKDIR/.dev.vars"

    echo "✅ .env and .dev.vars configured with local Supabase credentials."
    echo "   SUPABASE_URL  = ${api_url}"
    echo "   SUPABASE_KEY  = ${anon_key:0:20}..."
}

# ── Docker readiness ─────────────────────────────────────────────────────────
wait_for_docker() {
    local attempts=30 delay=2 last_error=""

    if ! command -v docker >/dev/null 2>&1; then
        echo "❌ Docker CLI is not available inside the devcontainer."
        echo "   Rebuild so the docker-outside-of-docker feature installs the Docker CLI."
        exit 1
    fi

    if [ ! -S /var/run/docker.sock ]; then
        echo "❌ Host Docker socket is not mounted inside the devcontainer."
        echo "   Make sure /var/run/docker.sock is mounted to /var/run/docker.sock."
        exit 1
    fi

    for i in $(seq 1 "$attempts"); do
        docker info >/dev/null 2>&1 && return 0
        last_error=$(docker info 2>&1 || true)
        [ "$i" -lt "$attempts" ] && echo "   Docker not ready; waiting ${delay}s (${i}/${attempts})..." && sleep "$delay"
    done

    echo "❌ Host Docker engine is not available inside the devcontainer."
    echo "$last_error"
    echo "   Start Docker on the host, then rebuild or restart the devcontainer."
    exit 1
}

# ═══════════════════════════════════════════════════════════════════════════════

echo "🗄️  Starting local Supabase stack using the host Docker engine..."

wait_for_docker

# Discover the host IP from the Kong container (or ip-route fallback)
SUPABASE_HOST=$(discover_supabase_host)
echo "ℹ️  Supabase host resolved to: ${SUPABASE_HOST}"

# If the stack is already running, set up forwards and check credentials
if has_running_supabase_stack; then
    echo "ℹ️  Supabase containers already running — setting up port forwards..."
    start_supabase_port_forwards "$SUPABASE_HOST"

    # Brief pause so socat can bind
    sleep 1

    if wait_for_supabase_api "127.0.0.1"; then
        ANON_KEY=$(derive_anon_key) && {
            write_env_vars "$(supabase_api_url)" "$ANON_KEY"
            echo "✅ Supabase is already running; reused existing local stack."
            exit 0
        }
    fi
fi

# Stack not running (or not reachable yet) — start it
stop_supabase_port_forwards
start_deferred_supabase_port_forwards "$SUPABASE_HOST"

echo "🚀 Running 'npx supabase start' (timeout 5 min)..."
# Capped at 5 min: in Docker-outside-of-Docker the CLI health check can block
# indefinitely because it cannot inspect containers by ID from inside the
# devcontainer. Stream output so the terminal doesn't appear frozen.
timeout 300 npx supabase start 2>&1 || START_EXIT=$?

if [ -n "${FORWARD_BOOTSTRAP_PID:-}" ] && pid_is_alive "$FORWARD_BOOTSTRAP_PID"; then
    kill "$FORWARD_BOOTSTRAP_PID" 2>/dev/null || true
    wait "$FORWARD_BOOTSTRAP_PID" 2>/dev/null || true
fi

if has_running_supabase_stack; then
    start_supabase_port_forwards "$SUPABASE_HOST"
fi

# Verify API is reachable and write credentials
if ! wait_for_supabase_api "127.0.0.1"; then
    if has_running_supabase_stack; then
        echo ""
        echo "⚠️  Supabase containers are running but Kong is not responding on localhost."
        echo "   Run: bash .devcontainer/scripts/fix-supabase-connection.sh"
        exit 0
    fi
    echo ""
    echo "❌ Supabase did not start correctly."
    [ -n "${START_EXIT:-}" ] && echo "   'npx supabase start' exited with code ${START_EXIT}."
    echo "   Run 'npx supabase start --debug' to diagnose."
    exit 1
fi

ANON_KEY=$(derive_anon_key) || {
    echo ""
    echo "⚠️  Supabase is running but could not read JWT_SECRET from the db container."
    echo "   Run: bash .devcontainer/scripts/fix-supabase-connection.sh"
    exit 0
}

write_env_vars "$(supabase_api_url)" "$ANON_KEY"
