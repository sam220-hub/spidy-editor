#!/usr/bin/env python3
"""Optional: the BiRefNet person matte for `behind` beats and the cutout effects.

    python scripts/setup_matte.py

Cross-platform twin of scripts/setup_matte.sh. Without it, behind beats fall back to
`hyperframes remove-background` (u2net: blobby edges, a jumpy outline) and cutout beats stop the
build. One-time: ~1.5 GB venv + ~1.1 GB weights (downloaded into the matte cache, never into the
repo: ~/.cache/ghost-matte, or %LOCALAPPDATA%\\ghost-editor\\ghost-matte on Windows).
Weights: BiRefNet-portrait + BiRefNet_lite, MIT. bria models are refused.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ghostenv  # noqa: E402
from setups import ensure_venv, pip_install, run_py  # noqa: E402


def main() -> int:
    venv = ghostenv.venv("ghost-matte", "MATTE_VENV")
    py = ensure_venv(venv)
    pip_install(venv, ["-r", str(HERE / "matte-requirements.txt")])
    # warm the weights so the first build does not stall on a download
    run_py(py, ["-c", f"import sys; sys.path.insert(0, {str(HERE)!r}); import matte; "
                      "matte.hf_dir('ZhengPeng7/BiRefNet-portrait'); print('weights ok:', matte.CACHE)"])
    # cutout beats default to BiRefNet_lite (+176 MB); the other models download on first use
    run_py(py, [str(HERE / "cutout_fx.py"), "--help"], stdout=subprocess.DEVNULL)
    run_py(py, ["-c", f"import sys; sys.path.insert(0, {str(HERE)!r}); import cutout_fx; "
                      "cutout_fx.weights_dir('lite'); print('cutout_fx weights ok')"])
    print(f"matte venv ready: {venv}  ({ghostenv.python_in(venv)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
