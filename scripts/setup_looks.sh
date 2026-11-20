#!/usr/bin/env bash
# Compatibility wrapper: the code lives in scripts/setup_looks.py, which also runs on Windows.
#   bash scripts/setup_looks.sh [gen_luts.py args]
exec python3 "$(cd "$(dirname "$0")" && pwd)/setup_looks.py" "$@"
