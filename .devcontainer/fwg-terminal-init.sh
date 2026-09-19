#!/usr/bin/env bash

FWG_ROOT="/workspaces/fwg_ai_os"
FWG_DEV_UP="$FWG_ROOT/.devcontainer/dev_up.sh"
FWG_DOCTOR="$FWG_ROOT/.devcontainer/fwg-doctor.sh"

if [ ! -f "$FWG_DOCTOR" ]; then
    return 0 2>/dev/null || exit 0
fi

echo
echo "============================================================"
echo " FWG-AI-OS TERMINAL STARTUP CHECK"
echo "============================================================"

if [ -f "$FWG_DEV_UP" ]; then
    echo "[terminal-init] Ensuring Docker stack is up..."
    bash "$FWG_DEV_UP" > /tmp/dev_up_last.log 2>&1
    DEV_UP_RESULT=$?
    if [ "$DEV_UP_RESULT" -ne 0 ]; then
        echo "🔴 dev_up.sh failed — see /tmp/dev_up_last.log"
        tail -20 /tmp/dev_up_last.log
    fi
fi

bash "$FWG_DOCTOR"

FWG_RESULT=$?

echo
if [ "$FWG_RESULT" -eq 0 ]; then
    echo "🟢 FWG-AI-OS READY"
else
    echo "🔴 FWG-AI-OS NEEDS ATTENTION"
    echo "   Run: bash .devcontainer/fwg-doctor.sh"
fi

echo "============================================================"
echo

return 0 2>/dev/null || exit 0
