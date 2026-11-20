#!/usr/bin/env python3
"""Check everything ghost-editor needs on this machine, and say how to fix what's missing.

    python scripts/doctor.py          (macOS: bash scripts/doctor.sh still works)

Cross-platform port of scripts/doctor.sh. Lines marked MISS end with the command that fixes them
(Homebrew on a Mac, winget on Windows, apt on Linux); `opt` lines are optional tools with their
own scripts/setup_<x>.py.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
S = HERE.parent
sys.path.insert(0, str(HERE))

import ghostenv  # noqa: E402

OK = BAD = 0
ROWS: list[str] = []


def say(text: str = "") -> None:
    print(text)
    ROWS.append(text)


def install_hint(mac: str, win: str, linux: str) -> str:
    return win if ghostenv.IS_WIN else (mac if ghostenv.IS_MAC else linux)


def pass_(msg: str) -> None:
    global OK
    OK += 1
    say(f"  ok    {msg}")


def fail(msg: str, fix: str) -> None:
    global BAD
    BAD += 1
    say(f"  MISS  {msg}  ->  {fix}")


def opt(msg: str) -> None:
    say(f"  opt   {msg}")


def out(cmd, **kw) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=kw.pop("timeout", 300), **kw)
        return (r.stdout or "") + (r.returncode and "\n" + (r.stderr or "") or "")
    except Exception:
        return ""


def grep_count(pattern: str, roots: list[Path], includes=("*.py", "*.sh", "*.mjs", "*.js")) -> list[str]:
    hits = []
    for root in roots:
        for inc in includes:
            for f in root.rglob(inc):
                if "node_modules" in f.parts:
                    continue
                try:
                    for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                        if re.search(pattern, line):
                            hits.append(f"{f}:{i}:{line.strip()[:160]}")
                except OSError:
                    continue
    return hits


def main() -> int:
    ghostenv.augment_path()
    py = os.environ.get("MEDIA_PY") or ghostenv.python_for_numpy()

    say("tools")
    ff = ghostenv.which("ffmpeg")
    if ff:
        ver = out([ff, "-version"]).splitlines()[:1]
        ver = ver[0].split()[2] if ver and len(ver[0].split()) > 2 else "?"
        pass_(f"ffmpeg {ver} ({ff})")
        bc = out([ff, "-hide_banner", "-buildconf"])
        pass_("ffmpeg libvpx (alpha WebM memes)") if "enable-libvpx" in bc else fail(
            "ffmpeg libvpx", install_hint("brew reinstall ffmpeg", "winget install Gyan.FFmpeg --force", "apt install ffmpeg"))
        pass_("ffmpeg libass") if "enable-libass" in bc else fail(
            "ffmpeg libass", install_hint("brew reinstall ffmpeg", "winget install Gyan.FFmpeg --force", "apt install ffmpeg"))
    else:
        fail("ffmpeg", install_hint("brew install ffmpeg", "winget install Gyan.FFmpeg", "sudo apt install ffmpeg"))

    node = ghostenv.which("node")
    node_major = 0
    if node:
        try:
            node_major = int(out([node, "-p", "process.versions.node.split('.')[0]"]).strip() or 0)
        except ValueError:
            node_major = 0
    if node and node_major >= 18:
        pass_(f"node {out([node, '-v']).strip()} ({node})")
    else:
        fail("node >= 18", install_hint("brew install node", "winget install OpenJS.NodeJS.LTS", "apt install nodejs"))

    # HyperFrames is pinned in ONE place (scripts/HF_VERSION), read by hf.py, hf_version.py and build.mjs
    hf_pin = (HERE / "HF_VERSION").read_text(encoding="utf-8").strip() if (HERE / "HF_VERSION").exists() else ""
    v = ""
    try:
        r = subprocess.run([sys.executable, str(HERE / "hf.py"), "--version"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=600)
        v = (r.stdout or "").strip().splitlines()[-1] if (r.stdout or "").strip() else ""
    except Exception:
        v = ""
    want = os.environ.get("HF_VERSION") or hf_pin
    if v and v == want:
        pass_(f"hyperframes {v} (pinned in scripts/HF_VERSION)")
    else:
        fail(f"hyperframes {hf_pin} (scripts/HF_VERSION)",
             f"python {HERE / 'hf.py'} --version (needs network once; npm must be on PATH)")
    if os.environ.get("HF_VERSION") and os.environ["HF_VERSION"] != hf_pin:
        say(f"  WARN  HF_VERSION={os.environ['HF_VERSION']} overrides scripts/HF_VERSION ({hf_pin}): renders here differ "
            "from the other machine; unset it after the test")

    un = [h for h in grep_count(r"npx (-y )?hyperframes([^@]|$)", [S]) if "unpinned" not in h.lower() and "instead of" not in h.lower()]
    if not un:
        pass_("no unpinned hyperframes calls in the skill")
    else:
        say("  WARN  unpinned hyperframes calls (use scripts/hf.py, or hf() from scripts/hf_version.py):")
        for h in un:
            say("          " + h)

    if ghostenv.IS_WIN:
        # HyperFrames renders in a Chromium browser; without one it downloads ~150 MB of Chrome on first use
        from hf_version import installed_browser  # noqa: E402  (same detection the render uses)
        envb = os.environ.get("HYPERFRAMES_BROWSER_PATH")
        found = installed_browser()
        if found:
            pass_(f"hyperframes browser ({found})")
        elif envb:
            fail("hyperframes browser", f"HYPERFRAMES_BROWSER_PATH={envb} does not exist: unset it or fix the path")
        else:
            opt("no Chrome/Edge found: the first render downloads Chrome (~150 MB; it waits on 'Checking browser...') -> "
                "winget install Microsoft.Edge")

    # x264's thread count is pinned in ONE place (scripts/X264_THREADS)
    xt = (HERE / "X264_THREADS").read_text(encoding="utf-8").strip() if (HERE / "X264_THREADS").exists() else ""
    bad_pins = [h for h in grep_count(r"(-c:v|-vcodec|-codec:v)[\"', ]*(libx264|h264_videotoolbox|hevc_videotoolbox)", [HERE, S / "recipes", S / "tests"])
                if not re.search(r"libx264[\"',\s]+-threads", h) and "doctor" not in h]
    hx = out([sys.executable, str(HERE / "hf_ffmpeg.py"), "--print-argv", "-i", "in.mp4", "-c:v", "libx264", "-preset", "medium", "out.mp4"]).strip()
    shim_ok = hx.endswith(f"-c:v libx264 -threads {xt} -preset medium out.mp4")
    if xt and not bad_pins and shim_ok:
        pass_(f"every libx264 encode uses -threads {xt} (scripts/X264_THREADS), HyperFrames' too (hf_ffmpeg.py)")
    elif not bad_pins and shim_ok and ghostenv.IS_WIN:
        pass_(f"every libx264 encode uses -threads {xt}; HyperFrames renders use the system ffmpeg on Windows")
    else:
        say("  WARN  x264 threads not pinned: these encodes give different bytes on each machine (pass -threads from "
            "scripts/X264_THREADS right after libx264; no hardware encoder):")
        if not xt:
            say("          scripts/X264_THREADS is missing or empty")
        if not shim_ok:
            say(f"          scripts/hf_ffmpeg.py does not add it to HyperFrames' encodes (got: {hx})")
        for h in bad_pins:
            say("          " + h)

    if ghostenv.IS_WIN:
        # Not fatal, but a cp1252 default encoding turns "é" in a caption or a project name into a crash
        utf8 = bool(sys.flags.utf8_mode) or os.environ.get("PYTHONUTF8") == "1"
        if utf8:
            pass_(f"python writes UTF-8 (mode {'utf-8' if sys.flags.utf8_mode else 'PYTHONUTF8=1'})")
        else:
            say("  WARN  python is not in UTF-8 mode: non-ASCII captions, titles or project paths can fail to write. "
                "Fix once: setx PYTHONUTF8 1 (new terminal), or run steps through `ghost`, which sets it")

    w = os.environ.get("WHISPER") or ghostenv.which("whisper")
    if w:
        pass_(f"whisper ({w})")
    else:
        fail("whisper", "pip install openai-whisper (or set WHISPER=/path/to/whisper)")
    if ghostenv.which("yt-dlp"):
        pass_(f"yt-dlp {out([ghostenv.which('yt-dlp'), '--version']).strip()}")
    else:
        opt("yt-dlp not installed: only needed to pull a reference video from a link -> "
            + install_hint("brew install yt-dlp", "winget install yt-dlp.yt-dlp", "pip install yt-dlp"))

    for mod, label, fix in (("numpy", "numpy", "pip install numpy"),
                            ("cv2", "opencv (face tracking)", "pip install opencv-python"),
                            ("google.genai", "google-genai", "pip install google-genai"),
                            ("PIL", "pillow", "pip install pillow")):
        r = subprocess.run([py, "-c", f"import {mod}"], capture_output=True)
        if r.returncode == 0:
            pass_(f"python {label} ({py})")
        elif mod == "numpy":
            fail(f"python {label}", fix)
        else:
            fail(f"python {label} (B-roll people/line checks, QA)" if mod == "google.genai" else f"python {label}",
                 f'"{py}" -m pip install {mod if mod != "PIL" else "pillow"}' if mod != "cv2" else f'"{py}" -m pip install opencv-python')

    say("keys")
    env_file = S / ".env"
    dotenv = env_file.read_text(encoding="utf-8", errors="replace") if env_file.exists() else ""

    def key(name: str) -> str | None:
        if os.environ.get(name):
            return os.environ[name]
        m = re.search(rf"^{name}\s*=\s*['\"]?([^'\"\n]+)", dotenv, re.M)
        return m.group(1).strip() if m else None

    gk = key("GEMINI_API_KEY")
    if gk:
        code = ("import os\nfrom google import genai\nfrom google.genai import types\n"
                "c = genai.Client(api_key=os.environ['K'], http_options=types.HttpOptions(timeout=30000))\n"
                "print((c.models.generate_content(model='gemini-2.5-flash', contents='Reply with the single word ok.').text or '').strip()[:20])")
        r = subprocess.run([py, "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, K=gk), timeout=300)
        res = ((r.stdout or "").strip() or (r.stderr or "").strip().splitlines()[-1:] or [""])
        res = res[0] if isinstance(res, list) else res
        if res.lower().startswith("ok"):
            pass_("GEMINI_API_KEY works (one test call)")
        else:
            fail(f"GEMINI_API_KEY is set but the test call failed: {res[:140]}",
                 f"check the key at aistudio.google.com/apikey (env or {env_file})")
    else:
        fail("GEMINI_API_KEY (insert_prep.py, broll_vision.py, broll_qa.py people/match: unchecked shots fail)",
             f"set GEMINI_API_KEY=... in the environment or in {env_file} (free key: aistudio.google.com/apikey)")

    if key("ELEVENLABS_API_KEY"):
        pass_("ELEVENLABS_API_KEY (narrated explainers)")
    else:
        opt(f"ELEVENLABS_API_KEY not set: only scripts/tts_elevenlabs.py (explainer voiceover) needs it -> {env_file}")

    df = ghostenv.venv_bin(ghostenv.venv("df", "DF_VENV", str(S / ".venv-df")), "deepFilter")
    if Path(df).exists():
        pass_("DeepFilterNet (scripts/denoise.py)")
    else:
        opt("DeepFilterNet not set up: scripts/denoise.py installs it on first use (needs python3.11 + uv)")

    say("optional tools (the core skill works without them)")
    if (S / "templates" / "vendor" / "hf-paper.js").exists():
        pass_("Paper Shaders bundle (templates/vendor/hf-paper.js)")
    else:
        fail("templates/vendor/hf-paper.js (shader looks)",
             "git checkout templates/vendor, or rebuild: cd tools/paper && npm install && node build-vendor.mjs")

    def count(glob: str) -> int:
        return len(list(S.glob(glob)))

    e = count("library/emoji/*.webm")
    if e >= 30:
        pass_(f"animated emoji ({e} Fluent webm)")
    else:
        opt(f"animated emoji not fetched ({e}): emoji beats fall back to the font glyph -> "
            f"{sys.executable} {HERE / 'emoji_fetch.py'} -I (needs ffmpeg libvpx-vp9)")
    lut = count("library/luts/*.cube")
    if lut >= 6:
        pass_(f"film-look LUTs ({lut} in library/luts)")
    else:
        opt(f"film-look LUTs not generated ({lut}): only look.film needs them -> python {HERE / 'setup_looks.py'}")

    setups = [
        ("MATTE_VENV", "ghost-matte", "BiRefNet matte (behind beats, cutout beats)",
         "behind beats fall back to hyperframes remove-background (u2net), cutout beats need it", "setup_matte"),
        ("AUDIOQA_VENV", "ghost-audioqa", "audio QA venv (vad_pauses, voice_enhance)",
         "only autocut --vad, vad_pauses.py and voice_enhance.py need it", "setup_audioqa"),
        ("CAPTIONS_VENV", "ghost-captions", "caption metrics venv (scripts/font_metrics.py)",
         "only needed to add a font to the caption templates", "setup_captions"),
    ]
    photo = 0
    for env_var, default, label, why, script in setups:
        vp = ghostenv.python_in(ghostenv.venv(default, env_var))
        if Path(vp).exists():
            pass_(label)
        else:
            opt(f"{label} not set up: {why} -> python {HERE / (script + '.py')}")

    mc = Path(os.environ.get("CUTOUT_FX_CACHE") or os.environ.get("GHOST_MATTE_CACHE")
              or str(ghostenv.cache_dir("ghost-matte")))
    mp = Path(ghostenv.python_in(ghostenv.venv("ghost-matte", "MATTE_VENV")))
    if mp.exists() and not (mc / "hf" / "BiRefNet_lite" / "model.safetensors").exists():
        opt(f"BiRefNet_lite weights not cached: cutout beats will download them (176 MB) on first use -> "
            f"python {HERE / 'setup_matte.py'}")

    say("recipes")
    fonts = ["inter-tight-cyrillic.woff2", "playfair-display-italic-cyrillic.woff2"]
    if all((S / "templates" / "fonts" / f).exists() for f in fonts):
        pass_("Seoul list / RESULT fonts (Inter Tight, Playfair Display, OFL)")
    else:
        fail("templates/fonts/" + " ".join(fonts), "git -C <skill> checkout templates/fonts")
    need = ["waving-hand", "hand-splayed", "point-right", "running", "yum", "eyes", "fire"]
    miss = [n for n in need if not (S / "library" / "emoji" / f"{n}.webm").exists()]
    if not miss:
        pass_("Seoul list emoji (hands, eyes, runner, yum, fire)")
    else:
        opt(f"Seoul list emoji missing ({','.join(miss)}) -> python {HERE / 'emoji_fetch.py'} -I --only {','.join(miss)}")
    if (S / "library" / "sfx" / "send-swoosh.wav").exists():
        pass_("Seoul list send sound (send-swoosh)")
    else:
        opt(f"send-swoosh not fetched (Seoul list outro) -> python {HERE / 'sfx_fetch.py'} --only send-swoosh")

    say("library")
    n = count("library/sfx/*.wav")
    if n >= 30:
        pass_(f"sfx kit ({n} files)")
    else:
        fail(f"sfx kit ({n} files)", f"python {HERE / 'library_restore.py'} --sfx-only")
    m = count("library/memes/*/clip.webm") + count("library/memes/*/image.png")
    if m >= 1:
        pass_(f"memes ({m})")
    elif (S / ".public-edition").exists():
        opt("memes: none (public edition; add clips you have rights to with scripts/meme_add.py)")
    else:
        fail("memes", f"python {HERE / 'library_restore.py'} --memes-only")
    if count("library/music/*.mp3"):
        pass_("music beds")
    else:
        fail("music beds", f"python {HERE / 'library_restore.py'} --music-only")

    say("toolchain vs the other machine (scripts/toolchain.py: records this one in library/toolchain/, compares)")
    tc = subprocess.run([sys.executable, str(HERE / "toolchain.py"), "compare"], capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    for line in (tc.stdout or "").splitlines():
        line = re.sub(r"^  DIFF ", "  WARN  ", line)
        line = re.sub(r"^  info ", "  info  ", line)
        line = re.sub(r"^vs ", "  ", line)
        line = re.sub(r"^no other", "  opt   no other", line)
        say(line)
    if tc.returncode:
        say("        the WARN lines change the edit (cut, mix or render); align them (docs/SYNC.md, Toolchain parity)")

    say()
    say(f"{OK} ok, {BAD} missing")
    return 0 if BAD == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
