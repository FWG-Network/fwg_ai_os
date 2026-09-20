#!/bin/bash
set -uo pipefail

echo "=== [dev_up] FWG AI OS — Environment Bootstrap ==="

DATA_ROOT="/tmp/docker-data"
DAEMON_JSON="/etc/docker/daemon.json"
COMPOSE_DIR="/workspaces/fwg_ai_os"

# --- 0. Ensure containerd is running FIRST (dockerd needs it) ---
ensure_containerd() {
    if pgrep -x containerd > /dev/null 2>&1; then
        echo "[dev_up] ✅ containerd already running."
        return 0
    fi

    echo "[dev_up] containerd not running — starting it..."
    sudo rm -f /run/containerd/containerd.sock 2>/dev/null
    sudo setsid containerd > /tmp/containerd.log 2>&1 < /dev/null &
    disown

    for i in $(seq 1 30); do
        if pgrep -x containerd > /dev/null 2>&1 && [ -S /run/containerd/containerd.sock ]; then
            echo "[dev_up] ✅ containerd is up."
            return 0
        fi
        sleep 1
    done

    echo "[dev_up] ❌ containerd failed to start within 30s — check /tmp/containerd.log"
    tail -20 /tmp/containerd.log
    exit 1
}

ensure_containerd

# --- 1. Ensure daemon.json is correct ---
NEED_RESTART=0
DESIRED_JSON='{
  "data-root": "'"$DATA_ROOT"'",
  "storage-driver": "overlay2"
}'

if [ ! -f "$DAEMON_JSON" ] || ! grep -q "$DATA_ROOT" "$DAEMON_JSON" 2>/dev/null || ! grep -q "overlay2" "$DAEMON_JSON" 2>/dev/null; then
    echo "[dev_up] Writing corrected daemon.json..."
    sudo mkdir -p /etc/docker
    echo "$DESIRED_JSON" | sudo tee "$DAEMON_JSON" > /dev/null
    NEED_RESTART=1
fi

# --- 2. Check if dockerd is already running against the right data-root ---
CURRENT_ROOT=$(docker info 2>/dev/null | grep "Docker Root Dir" | awk '{print $NF}')
if [ "$CURRENT_ROOT" != "$DATA_ROOT" ]; then
    NEED_RESTART=1
fi

# --- 3. Restart dockerd cleanly with setsid (survives terminal disconnect) ---
if [ "$NEED_RESTART" = "1" ] || ! pgrep -x dockerd > /dev/null; then
    echo "[dev_up] Restarting dockerd..."
    sudo pkill -9 dockerd 2>/dev/null
    sleep 2
    sudo mkdir -p "$DATA_ROOT"
    sudo setsid dockerd > /tmp/dockerd.log 2>&1 < /dev/null &
    disown

    echo "[dev_up] Waiting for dockerd to come up..."
    READY=0
    for i in $(seq 1 60); do
        if docker info > /dev/null 2>&1; then
            READY=1
            break
        fi
        sleep 2
    done

    if [ "$READY" != "1" ]; then
        echo "[dev_up] ❌ dockerd failed to start within 120s — check /tmp/dockerd.log"
        tail -20 /tmp/dockerd.log
        exit 1
    fi
else
    echo "[dev_up] ✅ dockerd already running correctly, skipping restart."
fi

echo "[dev_up] Docker root dir: $(docker info 2>/dev/null | grep 'Docker Root Dir')"

# --- 4. Validate docker-compose.yml BEFORE bringing anything up ---
cd "$COMPOSE_DIR" || { echo "[dev_up] ❌ Cannot cd to $COMPOSE_DIR"; exit 1; }

echo "[dev_up] Validating docker-compose.yml..."
if ! docker compose config -q; then
    echo "[dev_up] ❌ docker-compose.yml is invalid — fix the error above before continuing."
    exit 1
fi
echo "[dev_up] ✅ docker-compose.yml is valid."

# --- 5. Bring up all services ---
echo "[dev_up] Bringing up containers (db, redis, qdrant, api, worker)..."
docker compose up -d db redis qdrant api worker

# --- 6. Ensure Docker Compose bridge is reachable through legacy FORWARD ---
COMPOSE_BRIDGE=$(docker network inspect fwg_ai_os_default --format '{{index .Options "com.docker.network.bridge.name"}}' 2>/dev/null || true)

if [ -z "$COMPOSE_BRIDGE" ]; then
    COMPOSE_BRIDGE=$(docker network inspect fwg_ai_os_default --format '{{.Id}}' 2>/dev/null | cut -c1-12 | sed 's/^/br-/')
fi

if [ -n "$COMPOSE_BRIDGE" ] && command -v iptables-legacy >/dev/null 2>&1; then
    if sudo iptables-legacy -C FORWARD -i "$COMPOSE_BRIDGE" -o "$COMPOSE_BRIDGE" -j ACCEPT 2>/dev/null; then
        echo "[dev_up] ✅ legacy intra-bridge FORWARD rule already present for $COMPOSE_BRIDGE."
    else
        echo "[dev_up] Adding legacy intra-bridge FORWARD rule for $COMPOSE_BRIDGE..."
        sudo iptables-legacy -I FORWARD 1 -i "$COMPOSE_BRIDGE" -o "$COMPOSE_BRIDGE" -j ACCEPT
        echo "[dev_up] ✅ legacy intra-bridge FORWARD rule added."
    fi

    if sudo iptables-legacy -C FORWARD -i "$COMPOSE_BRIDGE" ! -o "$COMPOSE_BRIDGE" -j ACCEPT 2>/dev/null; then
        echo "[dev_up] ✅ legacy outbound FORWARD rule already present for $COMPOSE_BRIDGE."
    else
        echo "[dev_up] Adding legacy outbound FORWARD rule for $COMPOSE_BRIDGE..."
        sudo iptables-legacy -I FORWARD 2 -i "$COMPOSE_BRIDGE" ! -o "$COMPOSE_BRIDGE" -j ACCEPT
        echo "[dev_up] ✅ legacy outbound FORWARD rule added."
    fi

    if sudo iptables-legacy -C FORWARD -o "$COMPOSE_BRIDGE" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null; then
        echo "[dev_up] ✅ legacy return FORWARD rule already present for $COMPOSE_BRIDGE."
    else
        echo "[dev_up] Adding legacy return FORWARD rule for $COMPOSE_BRIDGE..."
        sudo iptables-legacy -I FORWARD 3 -o "$COMPOSE_BRIDGE" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
        echo "[dev_up] ✅ legacy return FORWARD rule added."
    fi
else
    echo "[dev_up] ⚠️ Could not determine Compose bridge or iptables-legacy is unavailable."
fi

# --- 7. Poll the API until it responds instead of a fixed sleep ---
echo "[dev_up] Waiting for API to respond on :8000..."
for i in $(seq 1 30); do
    if curl -sS -o /dev/null http://127.0.0.1:8000/os/status 2>/dev/null; then
        break
    fi
    sleep 2
done

echo "[dev_up] === Final status ==="
STATUS_JSON=$(curl -sS http://127.0.0.1:8000/os/status)
echo "$STATUS_JSON"

if echo "$STATUS_JSON" | grep -q '"status":"operational"'; then
    echo ""
    echo "[dev_up] 🎉 All systems operational."
else
    echo ""
    echo "[dev_up] ⚠️ Stack is up but status is not fully 'operational' — check the services above for anything offline/degraded."
fi
