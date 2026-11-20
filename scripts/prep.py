#!/usr/bin/env python3
"""Transcode a phone recording into the reel's source: 1080x1920, 30 fps, H.264, voice at -16 LUFS.

    python scripts/prep.py <recording> <project-dir>        -> <project>/assets/talk.mp4

Cross-platform twin of scripts/prep.sh (which now just calls this file): it works the same on
Windows, macOS and Linux. Normalizing the voice here, before any SFX is mixed, is what keeps the
SFX levels in build.mjs meaningful: the kit's role levels assume a -16 LUFS voice.

A portrait phone file is a landscape HEVC stream with a rotation tag; ffmpeg rotates before the
filter graph, so the target is 1080x1920. A landscape source is centre-cropped to 9:16. An HDR
source (iPhone HLG / PQ, BT.2020) is tone-mapped to SDR BT.709 first (grade_lib.py sdr-vf: a LUT,
since this ffmpeg has no zscale): one HDR plate would make the whole HyperFrames render HDR.
Keyframes every 1 s (-g 30): HyperFrames seeks every plate on every frame.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ghostenv  # noqa: E402


def probe(*args: str) -> str:
    return subprocess.run([ghostenv.tool("ffprobe"), "-v", "error", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: prep.py <recording> <project-dir>", file=sys.stderr)
        return 2
    src = os.path.abspath(os.path.expanduser(argv[0]))
    proj = os.path.abspath(os.path.expanduser(argv[1]))
    if not os.path.isfile(src):
        print(f"no such recording: {src}", file=sys.stderr)
        return 1
    out = os.path.join(proj, "assets", "talk.mp4")
    os.makedirs(os.path.join(proj, "assets"), exist_ok=True)
    os.makedirs(os.path.join(proj, "build"), exist_ok=True)

    wh = probe("-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", src)
    w, h = (int(x) for x in wh.split(",")[:2])
    rot = probe("-select_streams", "v:0", "-show_entries", "stream_side_data=rotation", "-of", "csv=p=0", src)
    rot = re.sub(r"[,\-\s]", "", rot.splitlines()[0]) if rot else "0"
    if rot in ("90", "270"):
        w, h = h, w
    dur = probe("-show_entries", "format=duration", "-of", "csv=p=0", src)
    print(f"source {w}x{h} (rotation {rot or 'none'}), {dur} s")
    if w < h:
        vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30"
    else:
        vf = "crop=ih*9/16:ih,scale=1080:1920,fps=30"
        print("landscape source: centre-cropping to 9:16")

    tr = probe("-select_streams", "v:0", "-show_entries", "stream=color_transfer", "-of", "csv=p=0", src)
    tr = tr.splitlines()[0].strip(",") if tr else ""
    if tr in ("arib-std-b67", "smpte2084"):
        try:
            import grade_lib  # numpy: tone-mapping the HDR source
        except ImportError:
            py = ghostenv.python_for_numpy()
            if py == sys.executable:
                print(f"HDR source ({tr}): tone-mapping needs python with numpy (pip install numpy, or set MEDIA_PY)", file=sys.stderr)
                return 1
            return subprocess.call([py, __file__, *argv])  # re-run in the numpy python
        cube = os.path.join(proj, "build", "sdr.cube")
        vf = f"{grade_lib.sdr_vf(src, cube)},{vf}"
        print(f"HDR source ({tr}): tone-mapped to SDR BT.709 (build/sdr.cube)")

    print("== measuring voice loudness")
    ffmpeg = ghostenv.tool("ffmpeg")
    m = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-i", src, "-vn",
                        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    block = re.search(r"\{[^{}]*\}", m.stderr[-4000:], re.S)
    if not block:
        print("could not measure loudness:\n" + m.stderr[-2000:], file=sys.stderr)
        return 1
    st = json.loads(block.group(0))
    print(f"input: {st['input_i']} LUFS, true peak {st['input_tp']} dBTP")
    af = ("loudnorm=I=-16:TP=-1.5:LRA=11:"
          f"measured_I={st['input_i']}:measured_TP={st['input_tp']}:measured_LRA={st['input_lra']}:"
          f"measured_thresh={st['input_thresh']}:offset={st['target_offset']}:linear=true,aresample=48000")

    # libx264 with the fixed thread count (scripts/x264.py): every machine writes the same bytes.
    threads = (HERE / "X264_THREADS").read_text(encoding="utf-8").strip() or "12"
    cmd = [ffmpeg, "-v", "error", "-y", "-i", src, "-vf", vf, "-c:v", "libx264", "-threads", threads,
           "-crf", "17", "-preset", "fast", "-pix_fmt", "yuv420p", "-g", "30", "-keyint_min", "30",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
           "-af", af, "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart", out]
    rc = subprocess.call(cmd)
    if rc:
        return rc
    print(f"-> {out}")
    print(probe("-show_entries", "stream=codec_name,width,height,r_frame_rate", "-of", "csv=p=0", out))
    e = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-i", out, "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in e.stderr.splitlines():
        if re.match(r"^\s+I:", line):
            print("output voice " + line.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
