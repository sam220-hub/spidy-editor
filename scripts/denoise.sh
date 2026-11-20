#!/usr/bin/env bash
# Compatibility wrapper: the code lives in scripts/denoise.py, which also runs on Windows.
#   bash scripts/denoise.sh <video-or-audio> <out.wav> [atten_db=20]
exec python3 "$(cd "$(dirname "$0")" && pwd)/denoise.py" "$@"
