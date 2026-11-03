#!/usr/bin/env bash
set -euo pipefail
AUDIO_ROOT="$(cd -- "$(dirname -- "$0")" && pwd)"
AUDIO_PYTHON="${SAYFE_VENV:-$HOME/venvs/sayfe_vision}/bin/python"
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
cd "$AUDIO_ROOT/.."
exec "$AUDIO_PYTHON" -s -B -m AudioDetection.app "$@"
