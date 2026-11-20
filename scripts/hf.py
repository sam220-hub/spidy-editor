#!/usr/bin/env python3
"""The pinned HyperFrames CLI, on every OS.

    python scripts/hf.py render -o build/reel.mp4
    python scripts/hf.py lint / snapshot / remove-background / render ...

= npx -y hyperframes@<scripts/HF_VERSION> ...  (an HF_VERSION env var overrides the file for one
test; scripts/doctor.py warns while it is set). On Windows npx is npx.cmd, which cmd.exe would run
with its own argument splitting, so ghostenv.npx_argv() uses npm's npx-cli.js through node instead
(and finds it even when PATH lacks the npm shims).

HyperFrames runs ffmpeg through scripts/hf_ffmpeg.py on macOS/Linux, which pins the audio mix's
input order (why: hf_mix_order.py) and x264's thread count. On Windows HYPERFRAMES_FFMPEG_PATH
has to be a real executable (HyperFrames runs it with execFileSync, which cannot start a .cmd),
so the variable is left pointing at the system ffmpeg: the renders are identical, only the
byte-for-byte parity with the other machine is not.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ghostenv  # noqa: E402
from hf_version import VERSION  # noqa: E402  (reads scripts/HF_VERSION, honours HF_VERSION)


def ffmpeg_override() -> str | None:
    """What HyperFrames should use as its ffmpeg: the pinning shim, or None where it can't run one."""
    if ghostenv.IS_WIN:
        return os.environ.get("HYPERFRAMES_FFMPEG_PATH") or None
    return os.environ.get("HYPERFRAMES_FFMPEG_PATH") or str(HERE / "hf_ffmpeg.sh")


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: hf.py <hyperframes command> [args...]   e.g. hf.py lint | hf.py render -o build/reel.mp4",
              file=sys.stderr)
        return 2
    ov = ffmpeg_override()
    if ov:
        os.environ["HYPERFRAMES_FFMPEG_PATH"] = ov
    ghostenv.augment_path()
    cmd = ghostenv.npx_argv("-y", f"hyperframes@{VERSION}", *argv)
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
