#!/usr/bin/env bash
set -euo pipefail
AUDIO_ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
AUDIO_PYTHON="${SAYFE_VENV:-$HOME/venvs/sayfe_vision}/bin/python"
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
exec "$AUDIO_PYTHON" -s -B "$AUDIO_ROOT/bootstrap.py" "$@"
