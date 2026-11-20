#!/usr/bin/env python3
"""Optional: the audio QA tools (scripts/vad_pauses.py, scripts/voice_enhance.py).

    python scripts/setup_audioqa.py [--no-clearvoice]

Cross-platform twin of scripts/setup_audioqa.sh. One venv (~1.2 GB with torch) plus weights in
the audio QA cache (~/.cache/ghost-audioqa, or %LOCALAPPDATA%\\ghost-editor\\ghost-audioqa on
Windows). Prints the venv's python path on the last line.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ghostenv  # noqa: E402
from setups import ensure_venv, pip_install, uv_venv  # noqa: E402

PKGS = ["clearvoice==0.1.2", "silero-vad==6.2.3", "torch==2.8.0", "torchaudio==2.8.0", "torchvision==0.23.0",
        "numpy==1.26.4", "pyloudnorm==0.2.0", "matplotlib==3.11.2", "python_speech_features==0.6",
        "opencv-python==4.10.0.84", "soundfile==0.12.1"]


def main(argv: list[str]) -> int:
    venv = ghostenv.venv("ghost-audioqa", "AUDIOQA_VENV")
    cache = Path(os.environ.get("GHOST_AUDIOQA_CACHE") or ghostenv.cache_dir("ghost-audioqa"))
    # pinned to the tested set: clearvoice's resolver otherwise picks mismatched torch/torchaudio ABIs
    uv_venv(venv, PKGS)
    py = ghostenv.python_in(venv)
    cache.mkdir(parents=True, exist_ok=True)
    if "--no-clearvoice" not in argv:
        subprocess.check_call([str(py), str(HERE / "voice_enhance.py"), "--fetch-only"],
                              env=dict(os.environ, GHOST_AUDIOQA_MODELS=str(cache / "clearvoice")))
    subprocess.check_call([str(py), "-c", "import silero_vad, clearvoice, python_speech_features, cv2"])
    print(str(py))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
