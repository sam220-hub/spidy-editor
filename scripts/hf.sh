#!/usr/bin/env bash
# Compatibility wrapper: the code lives in scripts/hf.py, which also runs on Windows.
#   bash scripts/hf.sh render -o build/reel.mp4
exec python3 "$(cd "$(dirname "$0")" && pwd)/hf.py" "$@"
