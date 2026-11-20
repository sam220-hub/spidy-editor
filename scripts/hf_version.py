"""The one HyperFrames CLI version every script lints, snapshots and renders with.

The version lives in scripts/HF_VERSION (one line). An HF_VERSION environment variable overrides it for a one-off test
(scripts/doctor.py warns while it is set). Unpinned `npx hyperframes` fetches whatever was published last, so two machines,
or one machine on two days, render the same reel differently, and a release whose tarball 404s fails a whole batch.

    from hf_version import VERSION, hf
    subprocess.run(hf("render", "-o", out), cwd=project)       # ["npx", "-y", "hyperframes@<VERSION>", "render", ...]

Importing this also points HyperFrames at scripts/hf_ffmpeg.sh (HYPERFRAMES_FFMPEG_PATH, unless already set), which
fixes the audio mix's input order so the same reel gets the same audio on every render (why: hf_mix_order.py).
On Windows HyperFrames needs a real .exe there (it starts the path with execFileSync, which cannot run a .cmd), so the
variable is left alone and the system ffmpeg is used; the render is the same, only byte parity is not.

On Windows it also points HyperFrames at the Chrome/Edge already installed (HYPERFRAMES_BROWSER_PATH, unless already
set): `render` otherwise downloads a managed Chrome (~150 MB) on first use, and on a slow or filtered network it waits
forever on "Checking browser...".
"""
import os

import ghostenv

HERE = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(HERE, "HF_VERSION")
PINNED = open(FILE, encoding="utf-8").read().strip()
VERSION = os.environ.get("HF_VERSION") or PINNED
if not ghostenv.IS_WIN:
    os.environ.setdefault("HYPERFRAMES_FFMPEG_PATH", os.path.join(HERE, "hf_ffmpeg.sh"))

CHROME_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "hyperframes", "chrome")


def installed_browser() -> str | None:
    """A Chromium browser already on this PC, or None when HyperFrames should fetch its own."""
    env = os.environ.get("HYPERFRAMES_BROWSER_PATH")
    if env and os.path.exists(env):
        return env
    if os.path.isdir(CHROME_CACHE) and os.listdir(CHROME_CACHE):
        return None        # HyperFrames' own Chrome is installed: prefer the pinned build
    local = os.environ.get("LOCALAPPDATA", "")
    program_files = [os.environ.get("PROGRAMFILES", r"C:\Program Files"),
                     os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")]
    candidates = [os.path.join(local, r"Google\Chrome\Application\chrome.exe")]
    for root in program_files:
        candidates += [os.path.join(root, r"Google\Chrome\Application\chrome.exe"),
                       os.path.join(root, r"Microsoft\Edge\Application\msedge.exe")]
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None


if ghostenv.IS_WIN:
    _browser = installed_browser()
    if _browser:
        os.environ.setdefault("HYPERFRAMES_BROWSER_PATH", _browser)


def hf(*args):
    """npx -y hyperframes@<VERSION> ... (on Windows through node + npm's npx-cli.js)"""
    return ghostenv.npx_argv("-y", f"hyperframes@{VERSION}", *args)
