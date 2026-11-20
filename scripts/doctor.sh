#!/usr/bin/env bash
# Compatibility wrapper: the code lives in scripts/doctor.py, which also runs on Windows.
#   bash scripts/doctor.sh
exec python3 "$(cd "$(dirname "$0")" && pwd)/doctor.py" "$@"
