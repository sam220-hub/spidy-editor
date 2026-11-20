#!/usr/bin/env bash
# Compatibility wrapper: the code lives in scripts/rawcut_prep.py, which also runs on Windows.
#   bash scripts/rawcut_prep.sh <recording.MOV> <project-dir> [--gem]
exec python3 "$(cd "$(dirname "$0")" && pwd)/rawcut_prep.py" "$@"
