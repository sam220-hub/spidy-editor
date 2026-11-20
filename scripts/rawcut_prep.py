#!/usr/bin/env python3
"""Raw-cut inputs from one phone recording (step 0 of references/take-selection.md).

    python scripts/rawcut_prep.py <recording.MOV> <project-dir> [--gem]

Cross-platform twin of scripts/rawcut_prep.sh.

  build/full.wav   48 kHz mono PCM: plan_cut.py, subcheck.py and voice_smooth.py cut the voice from it
  build/a16.wav    16 kHz mono PCM: vad_pauses.py and islands_tx.py
  build/proxy.mp4  1080x1920 (or 1920x1080) H.264, FRAME FOR FRAME with the recording (no fps change):
                   facescan.py reads row i = frame i and --pts puts the recording's true frame times on
                   the rows, so a dropped or added frame would shift every face flag after it. The
                   script checks the frame count and exits 1 on a mismatch.
  build/gem.mp4    with --gem: half-size copy for Gemini uploads

The picture is not tone-mapped or graded: the proxy is for analysis, the plates come from the
recording itself (assemble.py --plan). Apple silicon decodes/rotates/scales on the GPU
(VideoToolbox); Windows and Linux use the CPU. Either way the encode is libx264 with the fixed
thread count (scripts/x264.py).
"""
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ghostenv  # noqa: E402

X264 = (HERE / "X264_THREADS").read_text(encoding="utf-8").strip() or "12"


def out(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()


def probe(*args: str) -> str:
    return out([ghostenv.tool("ffprobe"), "-v", "error", *args])


def frames(path: str) -> str:
    got = probe("-select_streams", "v:0", "-count_packets", "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", path)
    return got.splitlines()[0].replace(",", "") if got else "0"


def usage() -> None:
    print(__doc__.strip().splitlines()[2].strip())


def main(argv: list[str]) -> int:
    if any(a in ("-h", "--help") for a in argv):
        usage()
        return 0
    if len(argv) < 2:
        usage()
        return 2
    src = os.path.abspath(os.path.expanduser(argv[0]))
    proj = os.path.abspath(os.path.expanduser(argv[1]))
    gem = "--gem" in argv[2:]
    ffmpeg = ghostenv.tool("ffmpeg")
    if not os.path.isfile(src):
        print(f"no such recording: {src}", file=sys.stderr)
        return 1
    build = Path(proj) / "build"
    build.mkdir(parents=True, exist_ok=True)

    wh = probe("-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", src)
    w, h = (int(x) for x in wh.split(",")[:2])
    rot = probe("-select_streams", "v:0", "-show_entries", "stream_side_data=rotation", "-of", "csv=p=0", src)
    rot = re.sub(r"[,\s]", "", rot.splitlines()[0]) if rot else "0"
    if rot in ("-90", "270", "90", "-270"):
        w, h = h, w
    if w < h:
        W, H = 1080, 1920
    else:
        W, H = 1920, 1080
    want = frames(src)
    dur = probe("-show_entries", "format=duration", "-of", "csv=p=0", src)
    print(f"source {w}x{h} (rotation {rot or 'none'}), {want} frames, {dur} s")

    subprocess.check_call([ffmpeg, "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "48000",
                           "-c:a", "pcm_s16le", str(build / "full.wav")])
    subprocess.check_call([ffmpeg, "-v", "error", "-y", "-i", str(build / "full.wav"), "-ac", "1", "-ar", "16000",
                           "-c:a", "pcm_s16le", str(build / "a16.wav")])
    print(f"-> build/full.wav, build/a16.wav ({probe('-show_entries', 'format=duration', '-of', 'csv=p=0', str(build / 'full.wav'))} s)")

    gpu = False
    filters = out([ffmpeg, "-hide_banner", "-filters"])
    if ghostenv.IS_MAC and "transpose_vt" in filters:
        # Apple silicon: decode, rotate and scale on the GPU (the same frames, ~4x faster on 4K HEVC)
        dirs = {"-90": "clock", "270": "clock", "90": "cclock", "-270": "cclock", "180": "reversal", "-180": "reversal"}
        d = dirs.get(rot, "")
        vf = (f"transpose_vt=dir={d}," if d else "") + f"scale_vt={W}:{H},hwdownload,format=nv12"
        rc = subprocess.run([ffmpeg, "-v", "error", "-y", "-display_rotation:v:0", "0", "-hwaccel", "videotoolbox",
                             "-hwaccel_output_format", "videotoolbox_vld", "-i", src, "-vf", vf, "-fps_mode", "passthrough",
                             "-c:v", "libx264", "-threads", X264, "-crf", "20", "-preset", "veryfast",
                             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(build / "proxy.mp4")]).returncode
        gpu = rc == 0
        if not gpu:
            print("VideoToolbox path failed; CPU decode")
    if not gpu:
        subprocess.check_call([ffmpeg, "-v", "error", "-y", "-i", src,
                               "-vf", f"scale={W}:{H}:flags=bicubic,format=yuv420p", "-fps_mode", "passthrough",
                               "-c:v", "libx264", "-threads", X264, "-crf", "20", "-preset", "veryfast",
                               "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(build / "proxy.mp4")])
    got = frames(str(build / "proxy.mp4"))
    print(f"-> build/proxy.mp4 {W}x{H}, {got} frames ({'GPU' if gpu else 'CPU'})")
    if got != want:
        print(f"FRAME COUNT MISMATCH: proxy {got}, recording {want} (facescan rows would drift)", file=sys.stderr)
        return 1

    if gem:
        subprocess.check_call([ffmpeg, "-v", "error", "-y", "-i", str(build / "proxy.mp4"),
                               "-vf", f"scale={W // 2}:{H // 2}", "-c:v", "libx264", "-threads", X264,
                               "-crf", "28", "-preset", "veryfast", "-c:a", "aac", "-b:a", "96k", "-ac", "1",
                               "-movflags", "+faststart", str(build / "gem.mp4")])
        print("-> build/gem.mp4")
    print(f'cut.json "source": "{src}"')
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
