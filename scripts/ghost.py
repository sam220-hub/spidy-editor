#!/usr/bin/env python3
"""One command for every step, on every OS.

    ghost doctor                          # what this machine is missing
    ghost prep IN.mp4 $P                  # transcode + voice at -16 LUFS
    ghost transcribe $P/assets/talk.mp4 --out $P/build/words.whisper.json
    ghost rawcut IN.mp4 $P                # scripted multi-take recording: voice + frame-exact proxy
    ghost denoise IN.mp4 $P/build/voice-clean.wav
    ghost build $P                        # the reel's index.html (scripts/build.mjs, through node)
    ghost hf render -o build/reel.mp4     # the pinned HyperFrames CLI
    ghost finals preview $P --out $P/finals --code R12 --style "Clean OS" --title "..."
    ghost setup matte                     # optional venvs: matte | looks | audioqa | captions
    ghost <name> ...                      # any other scripts/<name>.py

`ghost` is the platform-neutral name SKILL.md uses; `scripts/<name>.py` and the macOS
`scripts/<name>.sh` wrappers run the same code.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ghostenv  # noqa: E402

ALIASES = {
    "doctor": "doctor.py",
    "prep": "prep.py",
    "rawcut": "rawcut_prep.py",
    "rawcut_prep": "rawcut_prep.py",
    "denoise": "denoise.py",
    "hf": "hf.py",
    "build": "build.mjs",
    "library": "library_restore.py",
}
SETUPS = {"matte": "setup_matte.py", "looks": "setup_looks.py",
          "audioqa": "setup_audioqa.py", "captions": "setup_captions.py"}

USAGE = __doc__


def main(argv: list[str]) -> int:
    ghostenv.augment_path()
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE.strip())
        return 0 if argv else 2
    step, rest = argv[0], argv[1:]
    if step in ("setup", "venv"):
        if not rest or rest[0] not in SETUPS:
            print(f"usage: ghost setup {{{'|'.join(SETUPS)}}}", file=sys.stderr)
            return 2
        target, rest = SETUPS[rest[0]], rest[1:]
    elif step in ALIASES:
        target = ALIASES[step]
    else:
        target = step if step.endswith(".py") else step + ".py"
    script = HERE / target
    if not script.exists():
        print(f"no step named {step!r}. Try: ghost --help", file=sys.stderr)
        return 2
    if script.suffix == ".mjs":                  # node steps (build.mjs): node_argv also finds node off PATH
        return subprocess.call([*ghostenv.node_argv(), str(script), *rest])
    return subprocess.call([sys.executable, str(script), *rest])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
