#!/usr/bin/env python3
"""Optional: the small venv for scripts/font_metrics.py (regenerates scripts/lib/metrics.json).

    python scripts/setup_captions.py

Cross-platform twin of scripts/setup_captions.sh. Only needed after a font is added to
templates/fonts; the caption templates themselves need nothing.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ghostenv  # noqa: E402
from setups import ensure_venv, pip_install  # noqa: E402


def main() -> int:
    venv = ghostenv.venv("ghost-captions", "CAPTIONS_VENV")
    ensure_venv(venv)
    pip_install(venv, ["fonttools==4.66.1", "brotli==1.2.0"])
    py = ghostenv.python_in(venv)
    subprocess.check_call([str(py), "-c", "import fontTools, brotli"])
    print(f"captions venv ready: {venv}  ({py})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
