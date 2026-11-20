#!/usr/bin/env python3
"""The ffmpeg HyperFrames runs (HYPERFRAMES_FFMPEG_PATH), on every OS.

Port of scripts/hf_ffmpeg.sh (which now just calls this file), plus the --mix-pcm mode of
scripts/hf_mix_pcm.sh:

  python scripts/hf_ffmpeg.py <ffmpeg args...>              straight to the real ffmpeg, except
  python scripts/hf_ffmpeg.py --mix-pcm <ffmpeg args...>    HyperFrames' audio mix, kept as PCM

Every call goes straight to the real ffmpeg except HyperFrames' audio mix, which hf_mix_order.py
first puts in a fixed input order: HyperFrames lists the mix inputs in the order their prep
happened to finish, so one reel came out with a different AAC stream, and sometimes 0.6 dB
quieter, on every render. Details in hf_mix_order.py.

HyperFrames' libx264 encodes (the render, its cfr pass, video proxies) set no thread count, and
x264's automatic one follows the core count, so each machine wrote different bytes: -threads from
scripts/X264_THREADS goes in after every libx264 (why: x264.py).

Windows note: HyperFrames starts this path with execFileSync, which cannot run a .cmd/.bat, so on
a PC HYPERFRAMES_FFMPEG_PATH stays unset (system ffmpeg). Run this file by hand when you need the
pinning for a single encode.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ghostenv  # noqa: E402

THREADS = (HERE / "X264_THREADS").read_text(encoding="utf-8").strip() or "12"
MIX_FLAGS = ("-c:a", "-acodec", "-b:a")


def real_ffmpeg() -> str:
    return os.environ.get("HF_REAL_FFMPEG") or ghostenv.tool("ffmpeg")


def pin_threads(args: list[str]) -> list[str]:
    out: list[str] = []
    prev = ""
    for x in args:
        out.append(x)
        if prev in ("-vcodec", "-codec:v", "-c", "-codec") or prev.startswith("-c:v"):
            if x == "libx264":
                out += ["-threads", THREADS]
        prev = x
    return out


def is_mix(args: list[str]) -> bool:
    joined = " " + " ".join(args) + " "
    return " -/filter_complex " in joined or " -filter_complex_script " in joined


def run_mix(args: list[str], real: str) -> int:
    return subprocess.call([sys.executable, "-I", str(HERE / "hf_mix_order.py"), real, *args])


def run_pcm(args: list[str], real: str) -> int:
    """the mix once for the render, then the same mix again to 32-bit float PCM at $HF_MIX_PCM"""
    rc = run_mix(args, real)
    pcm = os.environ.get("HF_MIX_PCM")
    if rc or not pcm or os.path.exists(pcm):
        return rc
    keep: list[str] = []
    skip = False
    for i, x in enumerate(args):
        if skip:
            skip = False
            continue
        if x in MIX_FLAGS:
            skip = True
            continue
        if i == len(args) - 1:      # HyperFrames' own output
            continue
        keep.append(x)
    with open(os.devnull, "wb") as null:
        rc2 = subprocess.call([sys.executable, "-I", str(HERE / "hf_mix_order.py"), real, *keep,
                               "-acodec", "pcm_f32le", pcm], stdout=null, stderr=null)
    if rc2:
        try:
            os.remove(pcm)
        except OSError:
            pass
    return rc


def main(argv: list[str]) -> int:
    mode = "plain"
    if argv and argv[0] == "--mix-pcm":
        mode, argv = "pcm", argv[1:]
    elif argv and argv[0] == "--ffmpeg-path":
        print(real_ffmpeg())
        return 0
    elif argv and argv[0] == "--print-argv":
        # what this shim would run, for scripts/doctor.py (a bare `echo` is not a program on Windows)
        print(" ".join(pin_threads(argv[1:])))
        return 0
    args = pin_threads(argv)
    real = real_ffmpeg()
    if is_mix(args):
        rc = run_pcm(args, real) if mode == "pcm" else run_mix(args, real)
        return rc
    return subprocess.call([real, *args])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
