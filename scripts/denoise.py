#!/usr/bin/env python3
"""Speech denoise for outdoor takes (crickets, hum, wind): DeepFilterNet3, attenuation capped at 20 dB.

    python scripts/denoise.py <video-or-audio> <out.wav> [atten_db=20]

Cross-platform twin of scripts/denoise.sh. Full strength removes the noise but leaves a thin,
"watery" voice (A/B checked on reel-c007); 20 dB + a little low-mid warmth (done later in the
cut) sounds natural. First run creates a Python 3.11 venv at <skill>/.venv-df (no py3.13 wheel
exists; building needs Rust): macOS and Windows both need python3.11 + uv (`pip install uv`).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
S = HERE.parent
sys.path.insert(0, str(HERE))

import ghostenv  # noqa: E402


def find_py311() -> str | None:
    for cand in ("python3.11", "python3.12"):
        got = ghostenv.which(cand)
        if got:
            return got
    if ghostenv.IS_WIN:
        r = subprocess.run(["py", "-3.11", "-c", "import sys;print(sys.executable)"], capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout.strip()
        for base in (Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python",
                     Path("C:/Program Files/Python311")):
            for p in (base / "Python311" / "python.exe", Path("C:/Program Files/Python311/python.exe")):
                if p.is_file():
                    return str(p)
    return None


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: denoise.py <video-or-audio> <out.wav> [atten_db=20]", file=sys.stderr)
        return 2
    src, out = argv[0], argv[1]
    att = argv[2] if len(argv) > 2 else "20"
    venv = ghostenv.venv("df", "DF_VENV", str(S / ".venv-df"))
    df = ghostenv.venv_bin(venv, "deepFilter")
    if not Path(df).exists():
        py = find_py311()
        if not py:
            print("needs python3.11 (winget install Python.Python.3.11 / brew install python@3.11)", file=sys.stderr)
            return 1
        uv = ghostenv.which("uv")
        if not uv:
            print("needs uv (pip install uv)", file=sys.stderr)
            return 1
        print(f"setting up DeepFilterNet in {venv} (one time, ~1 GB with torch)...")
        subprocess.check_call([uv, "venv", "-q", "-p", py, venv])
        subprocess.check_call([uv, "pip", "install", "-q", "deepfilternet", "torch<2.6", "torchaudio<2.6", "soundfile"],
                              env=dict(os.environ, VIRTUAL_ENV=venv))
    tmp = Path(tempfile.mkdtemp(prefix="ghost-df-"))
    try:
        subprocess.check_call([ghostenv.tool("ffmpeg"), "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "48000",
                               str(tmp / "in.wav")])
        subprocess.run([str(df), str(tmp / "in.wav"), "--atten-lim", att, "-o", str(tmp / "out")],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        made = list((tmp / "out").glob("*.wav"))
        if not made:
            print("deepFilter produced no output: is the venv intact? (delete "
                  f"{venv} and run again)", file=sys.stderr)
            return 1
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(made[0]), out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for f in (src, out):
        r = subprocess.run([ghostenv.tool("ffmpeg"), "-hide_banner", "-nostats", "-i", f, "-af", "volumedetect", "-f", "null", "-"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        m = re.search(r"mean_volume: ([-0-9.]+) dB", r.stderr)
        print(f"{os.path.basename(f)}: {m.group(1) if m else '?'} dB mean")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
