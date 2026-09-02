#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
export SAYFE_PROJECT_ROOT="${SAYFE_PROJECT_ROOT:-$PWD}"

echo "========================================================"
echo " SAY:FE UI Integrated Demo"
echo "========================================================"

web_pid="$(lsof -nP -t -iTCP:5000 -sTCP:LISTEN 2>/dev/null | head -n 1 || true)"
if [ -n "$web_pid" ]; then
    web_command="$(ps -p "$web_pid" -o args= 2>/dev/null || true)"
    echo "SAY:FE Web UI is already running on port 5000 (PID $web_pid)."
    echo "Command: ${web_command:-unknown}"
    exit 0
fi

echo
echo "[1/2] Setting up nRF5340 Auracast ZH / VI..."
"$PYTHON" scripts/setup_auracast_zh_vi.py

echo
echo "[2/2] Starting SAY:FE Web UI..."
echo "Open http://127.0.0.1:5000 in this machine's browser."
echo

TOKENIZERS_PARALLELISM=false \
CONSTRUCTION_SAFETY_TRANSLATION_DEVICE="${CONSTRUCTION_SAFETY_TRANSLATION_DEVICE:-cuda}" \
PYTHONPATH=. \
exec "$PYTHON" src/ui/safety_web.py
