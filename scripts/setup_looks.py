#!/usr/bin/env python3
"""Optional: film-stock looks.

    python scripts/setup_looks.py [gen_luts.py args]

Cross-platform twin of scripts/setup_looks.sh. Creates the venv with Spectral Film LUT (MIT) and
generates the LUTs into library/luts/ (6 looks: full LUTs + split negative/grain/print LUTs for
the grain, ~25 MB, gitignored like the rest of library/). Applying a look afterwards needs only
ffmpeg (scripts/film_look.py). Transitions (scripts/transitions.py) need no setup.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ghostenv  # noqa: E402
from setups import base_python, ensure_venv, pip_install  # noqa: E402


def main(argv: list[str]) -> int:
    venv = ghostenv.venv("ghost-looks", "LOOKS_VENV")
    try:
        ensure_venv(venv, require_311=True)
        pip_install(venv, ["spectral_film_lut==0.18.12"])
    except subprocess.CalledProcessError as e:
        print(f"\nspectral_film_lut could not be installed ({e}). Film looks are optional: the rest of the skill "
              f"works. On Windows try PYTHON311=<python3.11.exe> python scripts/setup_looks.py", file=sys.stderr)
        return 1
    py = ghostenv.python_in(venv)
    rc = subprocess.call([str(py), str(HERE / "gen_luts.py"), *argv])
    if rc:
        return rc
    n = len(list((HERE.parent / "library" / "luts").glob("*.cube")))
    print(f"film looks ready: {n} LUTs in {HERE.parent / 'library' / 'luts'} (venv {venv}, python {base_python()})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
