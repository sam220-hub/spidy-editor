"""One place for everything that differs between Windows, macOS and Linux.

The skill was written on macOS: `python3`, `bash scripts/x.sh`, `~/.venvs/<name>/bin/python`,
`npx`, `open file`. Every script that needs one of those asks this module instead, so the same
code runs on a Mac and on a PC:

    from ghostenv import python_in, venv_python, npx_argv, open_path, link_file

Nothing here imports numpy/opencv: it must stay importable from any python (stdlib only).
"""
from __future__ import annotations

import contextlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

if IS_WIN:
    # Windows defaults the text encoding to the console code page (cp1252 here). Captions, titles and
    # project names are rarely ASCII, so every process started from this one asks for UTF-8.
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent


# ---------------------------------------------------------------- PATH / executables

def _winget_dirs(*patterns: str) -> list[Path]:
    """ffmpeg/git installed by winget live under %LOCALAPPDATA%\\Microsoft\\WinGet (Links or Packages)."""
    out: list[Path] = []
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        return out
    winget = Path(local) / "Microsoft" / "WinGet"
    links = winget / "Links"
    if links.is_dir():
        out.append(links)
    pkgs = winget / "Packages"
    if pkgs.is_dir():
        for pat in patterns:
            out.extend(sorted(pkgs.glob(pat)))
            out.extend(sorted(pkgs.glob(f"*/{pat}")))
    return out


def _registry_path() -> list[str]:
    """The User and Machine PATH values as the registry has them now.

    A long-running host (an editor, an OpenCode service) keeps the PATH it started with, so Python,
    Node or ffmpeg installed after that are invisible to it and "python" is only the Store alias.
    Reading the registry fixes this process without a restart; its children inherit the fixed PATH.
    """
    if not IS_WIN:
        return []
    try:
        import winreg
    except ImportError:
        return []
    keys = ((winreg.HKEY_CURRENT_USER, "Environment"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"))
    out: list[str] = []
    for root, sub in keys:
        try:
            with winreg.OpenKey(root, sub) as k:
                value, _ = winreg.QueryValueEx(k, "Path")
        except OSError:
            continue
        out.extend(os.path.expandvars(str(value)).split(os.pathsep))
    return [p for p in (d.strip() for d in out) if p and os.path.isdir(p)]


def _win_tool(name: str) -> str | None:
    exe = name if name.lower().endswith(".exe") else name + ".exe"
    found = shutil.which(exe) or shutil.which(name)
    if found:
        return found
    if IS_WIN:
        for d in _winget_dirs("ffmpeg-*/bin", "ffprobe-*/bin"):
            p = d / exe
            if p.is_file():
                return str(p)
    return None


def which(name: str) -> str | None:
    """shutil.which, plus the winget install folders on Windows (a fresh install is not on PATH yet)."""
    if IS_WIN:
        return _win_tool(name)
    return shutil.which(name)


def tool(name: str, hint: str | None = None) -> str:
    """An external binary or a readable error: tool("ffmpeg") -> 'C:\\...\\ffmpeg.exe'."""
    if name == "ffmpeg" and os.environ.get("GHOST_FFMPEG"):
        return os.environ["GHOST_FFMPEG"]
    if name == "ffprobe" and os.environ.get("GHOST_FFPROBE"):
        return os.environ["GHOST_FFPROBE"]
    got = which(name)
    if got:
        return got
    os_name = "winget install Gyan.FFmpeg" if IS_WIN else ("brew install ffmpeg" if IS_MAC else "apt install ffmpeg")
    raise SystemExit(f"{name} not found on PATH -> {hint or os_name}")


def augment_path() -> None:
    """Make this process see the tools on this PC, even when it started before they were installed.

    Merges the registry PATH first (Python, Node, npm, ffmpeg: a host that was already running has
    a stale copy) and then adds the winget ffmpeg/ffprobe folder if that is still missing.
    """
    if not IS_WIN:
        return
    have = [d for d in os.environ.get("PATH", "").split(os.pathsep) if d]
    seen = {d.casefold() for d in have}
    fresh = [d for d in _registry_path() if d.casefold() not in seen]
    if fresh:
        os.environ["PATH"] = os.pathsep.join(dict.fromkeys(fresh + have))
    for exe in ("ffmpeg.exe", "ffprobe.exe"):
        if not shutil.which(exe):
            got = _win_tool(exe[:-4])
            if got:
                os.environ["PATH"] = str(Path(got).parent) + os.pathsep + os.environ["PATH"]


# ---------------------------------------------------------------- python / venvs

def python_in(venv: str | os.PathLike) -> Path:
    """The interpreter inside a venv, whichever layout this OS uses (Scripts\\python.exe vs bin/python)."""
    p = Path(os.path.expanduser(str(venv)))
    return p / ("Scripts/python.exe" if IS_WIN else "bin/python")


def venv_bin(venv: str | os.PathLike, name: str) -> Path:
    """A console script inside a venv (deepFilter, pip, hyperframes ...)."""
    p = Path(os.path.expanduser(str(venv)))
    if IS_WIN:
        return p / "Scripts" / (name if name.lower().endswith((".exe", ".cmd", ".bat")) else name + ".exe")
    return p / "bin" / name


def venv(name: str, env_var: str | None = None, default: str | None = None) -> str:
    """~/.venvs/<name>, overridable through <ENV_VAR> (macOS keeps the same paths on purpose)."""
    if env_var and os.environ.get(env_var):
        return os.path.expanduser(os.environ[env_var])
    return os.path.expanduser(default or f"~/.venvs/{name}")


def media_python() -> str:
    """The python that has numpy (and opencv): $MEDIA_PY, ~/.venvs/media, else this interpreter."""
    env = os.environ.get("MEDIA_PY")
    if env and Path(os.path.expanduser(env)).exists():
        return os.path.expanduser(env)
    cand = python_in("~/.venvs/media")
    if cand.exists():
        return str(cand)
    return sys.executable


def has_module(python: str, module: str) -> bool:
    try:
        return subprocess.run([python, "-c", f"import {module}"], capture_output=True, timeout=60).returncode == 0
    except Exception:
        return False


def python_for_numpy() -> str:
    """This interpreter when it has numpy, else the media venv, else this one (the caller reports the ImportError)."""
    if has_module(sys.executable, "numpy"):
        return sys.executable
    cand = python_in("~/.venvs/media")
    if cand.exists() and has_module(str(cand), "numpy"):
        return str(cand)
    return sys.executable


# ---------------------------------------------------------------- subprocess helpers

def npx_argv(*args: str, npx: str | None = None) -> list[str]:
    """npx on every OS.

    Windows only has npx.cmd, and cmd.exe mangles arguments that contain spaces (".draft-R01 - Clean OS.mp4"
    became two words and the render died), so run npm's npx-cli.js with node instead; the .cmd is the fallback.
    """
    if IS_WIN:
        exe = npx or which("npx") or which("npx.cmd")
        if not exe:
            raise SystemExit("npx not found: install Node 18+ (winget install OpenJS.NodeJS.LTS)")
        node = which("node")
        if node:
            for cand in (Path(node).parent / "node_modules" / "npm" / "bin" / "npx-cli.js",
                         Path(exe).parent / "node_modules" / "npm" / "bin" / "npx-cli.js"):
                if cand.is_file():
                    return [node, str(cand), *args]
        return [os.environ.get("COMSPEC", "cmd.exe"), "/c", exe, *args]
    return [npx or "npx", *args]


def node_argv(*args: str) -> list[str]:
    exe = which("node")
    if not exe:
        raise SystemExit("node not found: install Node 18+ (winget install OpenJS.NodeJS.LTS)")
    return [exe, *args]


def run(cmd, **kw) -> subprocess.CompletedProcess:
    """subprocess.run with the text/encoding defaults this repo expects (Windows cp1252 broke the ffmpeg logs)."""
    kw.setdefault("text", True)
    kw.setdefault("encoding", "utf-8")
    kw.setdefault("errors", "replace")
    return subprocess.run(cmd, **kw)


def popen(cmd, **kw) -> subprocess.Popen:
    kw.setdefault("text", True)
    kw.setdefault("encoding", "utf-8")
    kw.setdefault("errors", "replace")
    return subprocess.Popen(cmd, **kw)


def venv_pythonpath() -> str:
    """PATH with this venv's Scripts/bin first, for ffmpeg-like console scripts."""
    return os.environ.get("PATH", "")


# ---------------------------------------------------------------- files, links, opening

def link_file(src: str | os.PathLike, dst: str | os.PathLike) -> None:
    """A cheap alias to a media file: symlink where allowed, hard link next, a copy last (Windows without dev mode)."""
    src, dst = Path(src), Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink():
        dst.unlink()
    elif dst.exists():
        return
    for attempt in (os.symlink, os.link):
        try:
            attempt(src, dst)
            return
        except (OSError, NotImplementedError, AttributeError):
            continue
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)


def open_path(path: str | os.PathLike) -> None:
    """Double-click equivalent: opens the approval page / preview in the user's browser or player."""
    p = str(path)
    try:
        if IS_WIN:
            os.startfile(p)  # noqa: S606 - the point is to hand the file to the shell
        elif IS_MAC:
            subprocess.run(["open", p], check=False)
        else:
            subprocess.run(["xdg-open", p], check=False)
    except Exception:
        print(f"open this file yourself: {p}")


def user_home() -> Path:
    return Path.home()


def cache_dir(name: str) -> Path:
    """~/.cache/<name> on unix, %LOCALAPPDATA%\\ghost-editor\\<name> on Windows (same env overrides as before)."""
    if IS_WIN:
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "ghost-editor"
    else:
        base = Path.home() / ".cache"
    return base / name


def font_candidates(*names: str) -> list[str]:
    """Existing font files from a list of per-OS paths (first hit wins in the caller)."""
    roots = []
    if IS_WIN:
        roots = [Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"]
    elif IS_MAC:
        roots = [Path("/System/Library/Fonts/Supplemental"), Path("/System/Library/Fonts"), Path("/Library/Fonts")]
    else:
        roots = [Path("/usr/share/fonts/truetype/dejavu"), Path("/usr/share/fonts/truetype/liberation")]
    out = []
    for n in names:
        for r in roots:
            p = r / n
            if p.is_file():
                out.append(str(p))
    return out


def first_font(*names: str) -> str | None:
    got = font_candidates(*names)
    return got[0] if got else None


# ---------------------------------------------------------------- locks

@contextlib.contextmanager
def file_lock(path: str | os.PathLike, timeout: float = 120.0, wait: float = 0.5):
    """An exclusive lock on a file that exists on every OS (fcntl on unix, msvcrt on Windows)."""
    p = str(path)
    f = open(p, "a+", encoding="utf-8")
    t0 = time.time()
    try:
        while True:
            try:
                if IS_WIN:
                    import msvcrt
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.time() - t0 > timeout:
                    raise SystemExit(f"{p} is locked by another writer for {timeout:.0f} s")
                time.sleep(wait)
        yield
    finally:
        try:
            if IS_WIN:
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_UN)
        finally:
            f.close()
