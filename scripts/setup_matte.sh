#!/usr/bin/env bash
# Compatibility wrapper: the code lives in scripts/setup_matte.py, which also runs on Windows.
#   bash scripts/setup_matte.sh
exec python3 "$(cd "$(dirname "$0")" && pwd)/setup_matte.py" "$@"
