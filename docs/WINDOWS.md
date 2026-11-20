# spidy-editor on Windows

The skill was written on macOS. Every step now has a Python implementation that runs the same code on
Windows, macOS and Linux, so a Windows machine needs **no Git Bash, no WSL, no MSYS and no C++ build
tools**: just Python, ffmpeg and Node from `winget`.

Tested on Windows 11 with Python 3.12.10, ffmpeg 9.0.2 (Gyan full build), Node 26 and Microsoft Edge.

---

## One-time setup

Open **PowerShell** (no administrator needed) and run:

```powershell
winget install Gyan.FFmpeg Python.Python.3.12 OpenJS.NodeJS.LTS
```

winget updates the user `PATH`, but the shell you ran it in does not see it yet. **Close that terminal
and open a new one** before the next step, or refresh it in place:

```powershell
$env:PATH = [Environment]::GetEnvironmentVariable('PATH','User') + ';' + [Environment]::GetEnvironmentVariable('PATH','Machine')
```

Then, from the skill folder:

```powershell
setx PYTHONUTF8 1                 # captions and project names are rarely ASCII; new terminals get UTF-8
python -m pip install -U numpy opencv-python pillow google-genai requests openai-whisper
python scripts\doctor.py          # 0 missing when you are done; `opt` lines are optional
python scripts\library_restore.py # SFX, music beds and the emoji set (~60 MB)
```

(`spidy.cmd` sets `PYTHONUTF8` itself, so `spidy ...` works without `setx`; the `setx` is for calling
`python scripts\x.py` directly.)

`openai-whisper` pulls PyTorch, so that one package is a few GB and a few minutes; it is the only big
download in the core install.

To get the short `spidy` command everywhere, add the skill folder to your user `PATH` once (Settings →
System → About → Advanced system settings → Environment Variables → `Path` → New → `D:\path\to\spidy-editor`),
then open a new terminal:

```powershell
spidy doctor
```

Otherwise call it by path: `D:\path\to\spidy-editor\spidy.cmd doctor` (or, equivalently,
`python D:\path\to\spidy-editor\scripts\ghost.py doctor`).

**Gemini key** (recommended, free tier; needed for the B-roll check, AI stills, style study):
put `GEMINI_API_KEY=<key>` in the skill's `.env`. Get a key at https://aistudio.google.com/apikey.
Without it the presets still work and the B-roll check is skipped.

---

## Command table

`$S` is the skill folder, `$P` the reel project. There is nothing to translate: on Windows a `.py`
step is `python <script>` where the macOS docs say `bash <script>.sh`.

| macOS docs | Windows |
| --- | --- |
| `bash $S/scripts/doctor.sh` | `python $S\scripts\doctor.py` |
| `bash $S/scripts/prep.sh IN.MOV $P` | `python $S\scripts\prep.py IN.MOV $P` |
| `bash $S/scripts/rawcut_prep.sh IN.MOV $P` | `python $S\scripts\rawcut_prep.py IN.MOV $P` |
| `bash $S/scripts/denoise.sh IN $P/build/voice-clean.wav` | `python $S\scripts\denoise.py IN $P\build\voice-clean.wav` |
| `$S/scripts/hf.sh render -o build/reel.mp4` | `python $S\scripts\hf.py render -o build/reel.mp4` |
| `bash $S/scripts/setup_matte.sh` | `python $S\scripts\setup_matte.py` |
| `bash $S/scripts/setup_looks.sh` | `python $S\scripts\setup_looks.py` |
| `bash $S/scripts/setup_audioqa.sh` | `python $S\scripts\setup_audioqa.py` |
| `bash $S/scripts/setup_captions.sh` | `python $S\scripts\setup_captions.py` |
| `python3 scripts/x.py ...` | `python scripts\x.py ...` |
| `spidy <step> ...` | `spidy <step> ...` (`spidy.cmd`) |
| `HF_VERSION=0.8.x ...` | `$env:HF_VERSION="0.8.x"` in PowerShell |
| `open <file>` | `start <file>` (scripts use `os.startfile` through `ghostenv.open_path`) |

Everything else in `SKILL.md` (`transcribe.py`, `autocut.py`, `finals.py`, `build.mjs`, `qa.py`,
`render_report.py`, the recipe generators) is the same command with `python` instead of `python3`.

Notes on paths in PowerShell:

- Quote paths with spaces: `"C:\Users\me\My Videos\r01"`.
- Forward slashes work in the arguments this skill passes to Python and ffmpeg (`C:/reels/r01`), and they
  avoid most backslash-escaping mistakes. Inside JSON or a `.js`/`.mjs` argument, write `C:/reels/r01`
  or double the backslashes (`C:\\reels\\r01`).
- Keep reel projects outside the skill folder.

---

## What is different (by design)

1. **`python`, not `python3`.** There is no `python3` on Windows; the Microsoft Store `python.exe`
   stub is skipped everywhere (`ghostenv.which`, `setups.base_python`) because it opens the Store
   instead of running anything. `spidy.cmd` looks for a real interpreter itself (PATH, then
   `%LOCALAPPDATA%\Programs\Python\Python3*`, then the `py` launcher), so it also works in an editor
   or service that started before Python was installed and still has the old PATH; `ghost.py` then
   refills PATH from the registry, so `node`, `npx` and `ffmpeg` are found there too.
2. **`npx` runs as `node ...\npm\bin\npx-cli.js`.** `npx` is `npx.cmd` on Windows, and going through
   `cmd.exe` splits arguments that contain spaces (`".draft-R01 - Clean OS.mp4"` came out as two
   words and the render died), so `ghostenv.npx_argv()` and `build.mjs` call npm's JS entry point
   with node, and only fall back to `cmd.exe /c npx.cmd` when that file is missing. The pinned
   HyperFrames version is unchanged (`scripts/HF_VERSION`).
3. **HyperFrames renders in the Edge or Chrome already on the PC.** `render` normally downloads a managed
   Chrome (~150 MB); on Windows `hf_version.py` points `HYPERFRAMES_BROWSER_PATH` at your Edge/Chrome
   instead, so the first render starts immediately. With neither browser installed, HyperFrames fetches its
   own: `winget install Microsoft.Edge` avoids the download.
4. **HyperFrames renders with the system ffmpeg, not the byte-parity shim.** HyperFrames takes
   `HYPERFRAMES_FFMPEG_PATH` as a single executable and runs `-version` on it; a `.sh` (or `.cmd`)
   shim cannot be that on Windows. So renders use the installed ffmpeg: the same picture and the same
   encoder settings, but **not byte-identical to a Mac render**. The skill's own encodes still pin
   `-threads $(cat scripts/X264_THREADS)`.
5. **The caption size/contrast check is skipped.** `broll_qa.py` reads captions with macOS Vision
   (`osascript`). On Windows that check is skipped with a note; every other QA check runs.
6. **Whisper is the CLI, not MLX.** `--backend mlx` is Apple-silicon only. On Windows run
   `python scripts\transcribe.py IN --out words.whisper.json` (it uses `openai-whisper`).
7. **DeepFilterNet (noise removal) wants Python 3.11.** `python scripts\denoise.py` sets up its own
   venv on first use; if the 3.11-only wheels fail, install 3.11 (`winget install Python.Python.3.11`)
   and set `PYTHON311` to its `python.exe`. `scripts\setup_audioqa.py` and `setup_matte.py` work on 3.12.
8. **No `nohup`.** Long renders are run as a tracked background job; from PowerShell that means
   `Start-Process -Wait` or the agent's own background shell, never a detached `Start-Process`
   without `-Wait`.
9. **Locking and linking are Windows-native.** `ghostenv.file_lock()` uses `msvcrt` instead of
   `fcntl`, and `ghostenv.link_file()` copies (or hardlinks) instead of `symlink` unless Developer
   Mode is on.
10. **Text files are opened as UTF-8 explicitly.** Python defaults `open()` to the console code page
    on Windows (cp1252 here), and a caption with an "é" or an emoji in the manifest then fails to
    read or write; every text `open()` in `scripts/` and `recipes/` passes `encoding="utf-8"`, and
    `ghostenv` sets `PYTHONUTF8` for the child processes it starts.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `python` opens the Microsoft Store | `winget install Python.Python.3.12`, then Settings → Apps → Advanced app settings → App execution aliases → turn off `python.exe` / `python3.exe`. `py -3` also works. `spidy doctor` works either way: the launcher skips the Store alias and finds the real install. |
| `npx` / `node` not found right after installing | Open a new terminal (PATH was updated after yours started). Inside a long-running editor or OpenCode session use `spidy ...`: it re-reads PATH from the registry, so `spidy build`, `spidy hf` and `spidy doctor` see the new install without a restart. |
| `ffmpeg` not on `PATH` | `scripts\doctor.py` still finds the winget package under `%LOCALAPPDATA%\Microsoft\WinGet\Packages`, and the scripts use that path. To have it everywhere, restart the terminal or reinstall with `winget install Gyan.FFmpeg --force`. |
| `UnicodeEncodeError` / `'charmap' codec can't encode` on a caption, a project path or an emoji | The console code page is cp1252. `setx PYTHONUTF8 1`, open a new terminal (or run the step through `spidy`, which sets it). |
| A render is "stuck" with no output | Long encodes are quiet by design; check the job's log. Don't kill it before the `reel.mp4` timestamp stops moving. |
| The first render sits on `Checking browser` for a long time | HyperFrames is downloading its own Chrome (~150 MB). Install a Chromium browser (`winget install Microsoft.Edge`) and re-run: the skill points HyperFrames at it, no download. `python scripts\hf.py browser ensure` downloads it on purpose. |
| `whisper` is very slow the first time | The default model is `turbo` (large-v3-turbo, ~1.5 GB); it downloads once into `%USERPROFILE%\.cache\whisper`. `--model base` (~74 MB) is much faster while you are testing. |
| Venv creation is very slow | Windows Defender scans every file written into `scripts\venvs`. Add the skill folder to Defender's exclusions if you use the optional venvs. |
| Paths over 260 characters | Enable long paths (`HKLM\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled=1`) or keep project paths short. |

Check the install with:

```powershell
python scripts\doctor.py
```

`MISS` lines end with the command that fixes them; `opt` lines are optional tools (film LUTs, matte,
audio QA venv, caption metrics, yt-dlp, extra emoji, extra SFX).

## Install it in OpenCode (or Claude Code)

OpenCode discovers skills in `~/.config/opencode/skills` (native), plus `~/.claude/skills` and
`~/.agents/skills` (compatibility). Point one of them at this folder with a junction instead of
copying it: one 150 MB media library, one `.env`, and every future fix is picked up at once.

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.config\opencode\skills" | Out-Null
cmd /c mklink /J "$env:USERPROFILE\.config\opencode\skills\spidy-editor" "D:\path\to\spidy-editor"
```

A junction needs no admin rights and no Developer Mode. The skill ID is the folder name
(`spidy-editor`), so `@spidy-editor` in a prompt loads it. Check what OpenCode registered:

```powershell
opencode api get /api/skill | ConvertFrom-Json | % data | Select-Object id, path
```

A copy (`Copy-Item -Recurse`) works too, but it duplicates the library and has to be repeated on
every update. Either way, call the skill through `spidy` (or `spidy.cmd`): it finds Python even in a
session that started before Python was installed.
