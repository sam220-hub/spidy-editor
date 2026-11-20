#!/usr/bin/env bash
# Compatibility wrapper: the code lives in scripts/setup_captions.py, which also runs on Windows.
#   bash scripts/setup_captions.sh
exec python3 "$(cd "$(dirname "$0")" && pwd)/setup_captions.py" "$@"
