#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

MODEL="$(find . -maxdepth 1 -type f \( -name '*.engine' -o -name '*.pt' \) | sort | head -n 1)"
if [ -z "$MODEL" ]; then
  echo "[ERROR] v.6 폴더 안에 .pt 또는 .engine 모델을 넣어주세요."
  exit 1
fi

echo "[MODEL] $MODEL"
echo "[AUDIO] B4:8C:9D:34:D6:48"
echo "[PI]    DC:A6:32:7F:85:01"
python3 web_main.py --camera 0 --width 640 --height 480 --model "$MODEL"
