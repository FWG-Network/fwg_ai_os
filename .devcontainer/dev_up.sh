#!/bin/bash
echo "=== Checking Docker daemon config ==="
NEED_RESTART=0

if [ ! -f /etc/docker/daemon.json ] || ! grep -q "/tmp/docker-data" /etc/docker/daemon.json 2>/dev/null; then
    echo "Fixing daemon.json..."
    sudo mkdir -p /etc/docker
    sudo tee /etc/docker/daemon.json > /dev/null <<'JSON'
{
  "data-root": "/tmp/docker-data"
}
JSON
    NEED_RESTART=1
fi

if ! docker info 2>/dev/null | grep -q "/tmp/docker-data"; then
    NEED_RESTART=1
fi

if [ "$NEED_RESTART" = "1" ] || ! pgrep -x dockerd > /dev/null; then
    echo "Restarting dockerd..."
    sudo pkill -9 dockerd 2>/dev/null
    sudo pkill -9 containerd 2>/dev/null
    sleep 3
    sudo mkdir -p /tmp/docker-data
    sudo nohup dockerd > /tmp/dockerd.log 2>&1 &
    disown
    for i in $(seq 1 15); do
        sleep 2
        docker info > /dev/null 2>&1 && break
    done
fi

echo "=== Docker status ==="
docker info 2>&1 | grep -iE "storage driver|docker root dir"

echo "=== Bringing up containers ==="
cd /workspaces/fwg_ai_os
docker compose up -d db redis qdrant api worker

echo "=== Waiting for API ==="
sleep 8
echo "=== Status check ==="
curl -sS http://127.0.0.1:8000/os/status
echo ""
