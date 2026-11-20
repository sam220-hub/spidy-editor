#!/usr/bin/env bash
# Compatibility wrapper: the code lives in scripts/setup_audioqa.py, which also runs on Windows.
#   bash scripts/setup_audioqa.sh [--no-clearvoice]
exec python3 "$(cd "$(dirname "$0")" && pwd)/setup_audioqa.py" "$@"
