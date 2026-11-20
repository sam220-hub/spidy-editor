#!/usr/bin/env bash
# Compatibility wrapper: the code lives in scripts/prep.py, which also runs on Windows.
#   bash scripts/prep.sh <recording> <project-dir>
exec python3 "$(cd "$(dirname "$0")" && pwd)/prep.py" "$@"
