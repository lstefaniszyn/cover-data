#!/bin/bash
# Fix Supabase connectivity from inside the devcontainer when socat port
# forwards are dead (zombie processes) and host.docker.internal doesn't route.
#
# Strategy:
#   1. Detect the Docker host gateway IP (the host that owns the bound ports).
#   2. Verify Supabase is reachable at that IP.
#   3. Kill zombie socat PIDs and start fresh port forwards via the gateway IP.
#   4. Derive the anon key from the JWT secret in the running db container.
#   5. Write SUPABASE_URL / SUPABASE_KEY to .env and .dev.vars.

set -e

WORKDIR="/workspaces/app"
cd "$WORKDIR"

PROJECT_ID=$(awk -F '"' '/^project_id = / {print $2}' "$WORKDIR/supabase/config.toml")
PROJECT_ID=${PROJECT_ID:-$(basename "$WORKDIR")}
SUPABASE_PORTS=(54320 54321 54322 54323 54324)
API_PORT=54321

# ── 1. Find the Docker host gateway IP ──────────────────────────────────────

GATEWAY_IP=$(ip route | awk '/^default via/ {print $3; exit}')
if [ -z "$GATEWAY_IP" ]; then
    echo "❌ Could not determine the Docker host gateway IP."
    exit 1
fi
echo "ℹ️  Docker host gateway: ${GATEWAY_IP}"

# ── 2. Verify Supabase Kong is reachable at that IP ─────────────────────────

echo "🔍 Checking Supabase API at ${GATEWAY_IP}:${API_PORT} ..."
for attempt in $(seq 1 10); do
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 \
        "http://${GATEWAY_IP}:${API_PORT}/" 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" != "000" ]; then
        echo "✅ Supabase Kong responded (HTTP ${HTTP_CODE})."
        break
    fi
    echo "   Attempt ${attempt}/10 — not reachable yet; waiting 3s..."
    sleep 3
done

if [ "$HTTP_CODE" = "000" ]; then
    echo ""
    echo "❌ Cannot reach Supabase Kong at ${GATEWAY_IP}:${API_PORT}."
    echo "   Make sure the Supabase stack is running on the host:"
    echo "     docker ps | grep supabase_kong_${PROJECT_ID}"
    exit 1
fi

# ── 3. Derive the anon key from the db container's JWT secret ───────────────

echo "🔑 Deriving anon key from db container JWT secret..."

JWT_SECRET=$(docker exec "supabase_db_${PROJECT_ID}" env 2>/dev/null \
    | grep '^JWT_SECRET=' | cut -d= -f2-)

if [ -z "$JWT_SECRET" ]; then
    echo "❌ Could not read JWT_SECRET from supabase_db_${PROJECT_ID}."
    echo "   Is the container running?"
    exit 1
fi

# Generate HS256 JWT: header.payload.signature
# Payload: {"role":"anon","iss":"supabase","iat":1441827000,"exp":1809843200}
ANON_KEY=$(python3 - "$JWT_SECRET" <<'PYEOF'
import sys, base64, json, hmac, hashlib

def b64url(data):
    if isinstance(data, str):
        data = data.encode()
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

secret = sys.argv[1]
header  = b64url(json.dumps({"alg":"HS256","typ":"JWT"}, separators=(',',':')))
payload = b64url(json.dumps({"role":"anon","iss":"supabase","iat":1441827000,"exp":1809843200}, separators=(',',':')))
sig     = b64url(hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
print(f"{header}.{payload}.{sig}")
PYEOF
)

# Quick verify: the API should accept this key
VERIFY_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 \
    "http://${GATEWAY_IP}:${API_PORT}/rest/v1/" \
    -H "apikey: ${ANON_KEY}" \
    -H "Authorization: Bearer ${ANON_KEY}" 2>/dev/null || echo "000")

if [ "$VERIFY_CODE" = "000" ] || [ "$VERIFY_CODE" = "401" ]; then
    echo "❌ Generated anon key was rejected by the API (HTTP ${VERIFY_CODE})."
    echo "   The JWT secret may differ. Check the db container env manually:"
    echo "     docker exec supabase_db_${PROJECT_ID} env | grep JWT_SECRET"
    exit 1
fi
echo "✅ Anon key verified (HTTP ${VERIFY_CODE})."

# ── 4. Restart socat port forwards via the gateway IP ───────────────────────

echo "🔄 Restarting socat port forwards → ${GATEWAY_IP}..."

is_zombie() {
    local pid="$1"
    # Read the process state from /proc/<pid>/stat; field 3 is the state char.
    local state
    state=$(awk '{print $3}' /proc/"$pid"/stat 2>/dev/null || echo "")
    [ "$state" = "Z" ]
}

for port in "${SUPABASE_PORTS[@]}"; do
    pid_file="/tmp/supabase-${PROJECT_ID}-${port}.pid"

    # Kill any existing socat for this port (including zombies — just clean up)
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if [ -n "$pid" ]; then
            if is_zombie "$pid"; then
                echo "   Port ${port}: socat PID ${pid} is a zombie — cleaning up."
            elif kill -0 "$pid" 2>/dev/null; then
                kill "$pid" 2>/dev/null || true
            fi
        fi
        rm -f "$pid_file"
    fi

    # Also kill any leftover socat bound to this port that we don't track
    fuser -k "${port}/tcp" 2>/dev/null || true

    socat "TCP-LISTEN:${port},fork,reuseaddr,bind=127.0.0.1" \
          "TCP:${GATEWAY_IP}:${port}" \
          >"/tmp/supabase-${PROJECT_ID}-${port}.log" 2>&1 &
    echo "$!" > "$pid_file"
    echo "   Port ${port}: socat started (PID $!)."
done

sleep 1  # give socat a moment to bind

# ── 5. Verify the loopback forwards work ────────────────────────────────────

echo "🔍 Verifying loopback connectivity on 127.0.0.1:${API_PORT} ..."
for attempt in $(seq 1 10); do
    LB_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 \
        "http://127.0.0.1:${API_PORT}/rest/v1/" \
        -H "apikey: ${ANON_KEY}" \
        -H "Authorization: Bearer ${ANON_KEY}" 2>/dev/null || echo "000")
    if [ "$LB_CODE" != "000" ]; then
        echo "✅ Loopback forward working (HTTP ${LB_CODE})."
        break
    fi
    echo "   Attempt ${attempt}/10 — not ready yet; waiting 2s..."
    sleep 2
done

if [ "$LB_CODE" = "000" ]; then
    echo ""
    echo "⚠️  Loopback forward on 127.0.0.1:${API_PORT} is not responding."
    echo "   The socat processes started but may need more time."
    echo "   Try: curl -s http://127.0.0.1:${API_PORT}/rest/v1/ -H 'apikey: ${ANON_KEY}'"
fi

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

# ── 6. Write .env and .dev.vars ─────────────────────────────────────────────

if connect_app_to_supabase_network; then
    API_URL="http://supabase_kong_${PROJECT_ID}:8000"
else
    API_URL="http://127.0.0.1:${API_PORT}"
fi

[ -f "$WORKDIR/.env" ]      || cp "$WORKDIR/.env.example"      "$WORKDIR/.env"
[ -f "$WORKDIR/.dev.vars" ] || cp "$WORKDIR/.dev.vars.example" "$WORKDIR/.dev.vars"

sed -i "s|SUPABASE_URL=.*|SUPABASE_URL=${API_URL}|"   "$WORKDIR/.env"
sed -i "s|SUPABASE_KEY=.*|SUPABASE_KEY=${ANON_KEY}|"  "$WORKDIR/.env"
sed -i "s|SUPABASE_URL=.*|SUPABASE_URL=${API_URL}|"   "$WORKDIR/.dev.vars"
sed -i "s|SUPABASE_KEY=.*|SUPABASE_KEY=${ANON_KEY}|"  "$WORKDIR/.dev.vars"

echo ""
echo "✅ Done. .env and .dev.vars updated:"
echo "   SUPABASE_URL = ${API_URL}"
echo "   SUPABASE_KEY = ${ANON_KEY:0:30}..."
