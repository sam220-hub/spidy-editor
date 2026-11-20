"""Shared steps for scripts/setup_*.py: create a venv, install into it, run something in it.

The venv layout differs per OS (Scripts\\python.exe on Windows, bin/python elsewhere), so the
setup scripts never build those paths by hand.
"""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ghostenv  # noqa: E402


def base_python() -> str:
    """The interpreter a new venv is built from: $PYTHON311, else 3.11, else this python.

    The optional tools pin 3.11 in some places (DeepFilterNet, spectral_film_lut) but 3.12 works
    for the matte, audio QA and caption venvs; only complain when the caller passes require=.
    """
    env = os.environ.get("PYTHON311") or os.environ.get("PYTHON")
    if env:
        return env
    for name in ("python3.11", "python3.12", "python3", "python"):
        got = ghostenv.which(name)
        if got:
            # skip the Windows Store stub: it is a 0-byte alias that opens the Store instead
            if ghostenv.IS_WIN and "WindowsApps" in got:
                continue
            return got
    return sys.executable


def ensure_venv(venv: str, require_311: bool = False) -> str:
    """Create <venv> when it is missing (or broken) and return the interpreter inside it."""
    py = ghostenv.python_in(venv)
    if Path(py).exists():
        return str(py)
    base = base_python()
    if require_311:
        r = subprocess.run([base, "-c", "import sys;print(sys.version_info[:2])"], capture_output=True, text=True)
        if "(3, 11)" not in (r.stdout or ""):
            print(f"warning: {base} is not python 3.11; some wheels for this tool are 3.11-only "
                  f"(set PYTHON311=/path/to/python3.11)", file=sys.stderr)
    print(f"creating venv {venv} from {base}")
    subprocess.check_call([base, "-m", "venv", venv])
    return py


def pip_install(venv: str, args: list[str]) -> None:
    py = ghostenv.python_in(venv)
    subprocess.check_call([str(py), "-m", "pip", "install", "-q", "--upgrade", "pip"])
    cmd = [str(py), "-m", "pip", "install", "-q", *args]
    print("+ " + " ".join(args))
    subprocess.check_call(cmd)


def run_py(py: str, args: list[str], **kw) -> int:
    return subprocess.call([py, *args], **kw)


def uv_venv(venv: str, packages: list[str], python: str | None = None) -> None:
    """Prefer uv when installed (much faster, and the audio QA pin assumes it)."""
    uv = ghostenv.which("uv")
    if uv:
        if not Path(ghostenv.python_in(venv)).exists():
            subprocess.check_call([uv, "venv", "-q", "-p", python or base_python(), venv])
        subprocess.check_call([uv, "pip", "install", "-q", *packages], env=dict(os.environ, VIRTUAL_ENV=venv))
    else:
        ensure_venv(venv)
        pip_install(venv, packages)
