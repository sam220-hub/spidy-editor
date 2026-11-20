# Installing spidy-editor

The easy way: paste this into [OpenCode](https://opencode.ai) or [Claude Code](https://claude.com/claude-code):

> Install the spidy-editor skill: clone https://github.com/sam220-hub/spidy-editor into
> ~/.config/opencode/skills/spidy-editor (or ~/.claude/skills/spidy-editor) and follow its docs/INSTALL.md.

Your agent does the rest and tells you if it needs anything from you.

Your agent does the rest and tells you if it needs anything from you.

---

## For the agent doing the install

Work through these steps in order. Tell the user in plain words what you're installing and why.

1. **Clone** (skip if already there):
   ```bash
   git clone https://github.com/sam220-hub/spidy-editor ~/.config/opencode/skills/spidy-editor
   ```
   (For Claude Code, clone into `~/.claude/skills/spidy-editor` instead; both are discovered.)
2. **Check what's missing:**
   ```bash
   bash ~/.config/opencode/skills/spidy-editor/scripts/doctor.sh
   ```
   Every `MISS` line ends with the command that fixes it. Run those.
   - On a Mac they use Homebrew. If `brew` is missing, ask the user to install it from https://brew.sh first (it needs their password).
   - On Windows they use winget (see the Windows section below): `winget install Gyan.FFmpeg Python.Python.3.12 OpenJS.NodeJS.LTS`.
   - Install Python packages with `pip install` (or `pip3`). If pip refuses with "externally managed environment", use `pip install --user`, or ask the user whether they prefer a virtualenv.
3. **Download the sound effects, music and animated emoji** (free Mixkit licence and Microsoft's MIT Fluent emoji, ~60 MB):
   ```bash
   python3 ~/.config/opencode/skills/spidy-editor/scripts/library_restore.py
   ```
4. **Run `doctor.sh` again** (Windows: `python scripts\doctor.py`) until it ends with `0 missing`. Lines marked `opt` are optional.
5. **Gemini key (recommended, free tier).** It runs the B-roll check (each shot matches its line and keeps the user's
   people rules), finds the user's own footage by what is in it, copies the look of a reel they show you, and makes AI
   B-roll stills. Without it the presets work and the B-roll check is skipped. Ask the user for one:
   - they get a free key at https://aistudio.google.com/apikey
   - `pip install google-genai pillow`
   - save it with `echo 'GEMINI_API_KEY=<key>' >> ~/.config/opencode/skills/spidy-editor/.env` (the file is gitignored)
   - tell them the frames being checked are sent to Google.
   Then ask whether they have rules for who or what may appear in B-roll (for example no women, no children, no flags or
   religious symbols). If they do, write them into `people-rules.json` in the format of `people-rules.example.json`;
   if not, leave it empty. Never add rules they didn't ask for.
6. **ElevenLabs key (optional).** Only for the vector explainer's narrator. If the user wants it: a key from elevenlabs.io (Profile → API keys),
   saved as `ELEVENLABS_API_KEY=<key>` in the same `.env`. Noise removal (`scripts/denoise.sh`, Windows:
   `python scripts\denoise.py`) needs no key; it sets itself up on first use
   (python3.11 + uv, about 1 GB).
7. **Optional extras (ask first; each is one command and sets up its own venv, weights go to `~/.cache`):**
   - `bash scripts/setup_looks.sh`: film-stock looks (generates the LUTs, ~1 GB venv, a minute).
   - `bash scripts/setup_matte.sh`: the clean person cut-out for words behind the speaker (~2.4 GB with the model).
   - `bash scripts/setup_audioqa.sh`: pause detection on noisy recordings and voice super-resolution (~1.9 GB).
   - `bash scripts/setup_captions.sh`: only to add a new font to the caption templates.
   On Windows the same four are `python scripts\setup_looks.py`, `setup_matte.py`, `setup_audioqa.py`,
   `setup_captions.py`.
   Without them everything else works; `doctor.sh` lists them as `opt`.
8. **Tell the user it's ready**, and that they can now say, for example: "Edit ~/Downloads/my-video.mov into a reel."

Restart the agent (OpenCode or Claude Code) if it was already running before the clone, so the new skill
is discovered.

---

## Windows

Everything above works on Windows; three things change. Full detail, including troubleshooting, is in
[`WINDOWS.md`](WINDOWS.md).

1. **Toolchain** comes from winget instead of Homebrew:
   ```powershell
   winget install Gyan.FFmpeg Python.Python.3.12 OpenJS.NodeJS.LTS
   ```
   Then **open a new terminal** (winget updates `PATH` after your shell started) and:
   ```powershell
   setx PYTHONUTF8 1
   cd D:\path\to\spidy-editor
   python -m pip install -U numpy opencv-python pillow google-genai requests openai-whisper
   python scripts\doctor.py
   python scripts\library_restore.py
   ```
   No Git Bash, WSL or build tools. `openai-whisper` pulls PyTorch and is the only multi-GB download.
2. **`python`, not `python3`**, and `.py` instead of `.sh`: `python scripts\prep.py IN.MOV $P` where the
   macOS docs say `bash scripts/prep.sh IN.MOV $P`. Every `.sh` file is a thin wrapper around its `.py`
   twin, so macOS instructions keep working. `spidy.cmd` gives the short form: `spidy doctor`,
   `spidy prep IN.mov $P`, `spidy hf render -o build/reel.mp4`.
3. **A few macOS-only pieces are skipped, never faked:** MLX whisper (use the whisper CLI),
   macOS Vision OCR for broll_qa's caption size/contrast check (skipped with a note), and the
   `hf_ffmpeg.sh` byte-parity shim (HyperFrames needs a real `.exe`, so Windows renders use the
   system ffmpeg: same picture, not the same bytes). The cut, captions, SFX, QA and delivery are the
   same code.

DeepFilterNet (`scripts\denoise.py`) pins Python 3.11: `winget install Python.Python.3.11` and set
`PYTHON311` if its wheels refuse to build. The other optional venvs work on 3.12.

---

## Doing it by hand

You need a Mac with Apple silicon or a Windows 10/11 PC (macOS is what it is built and tested on; on
Windows the caption size/contrast check is skipped because it uses macOS text recognition) with:
- ffmpeg (with libvpx and libass): `brew install ffmpeg` / `winget install Gyan.FFmpeg`
- Node 18 or newer: `brew install node` / `winget install OpenJS.NodeJS.LTS`
- Whisper: `pip install openai-whisper`
- Python packages: `pip install numpy opencv-python pillow`
- Recommended: `pip install google-genai` and a Gemini key (see above); optional: `brew install yt-dlp`
  (`winget install yt-dlp.yt-dlp`) to pull reference videos from a link

```bash
git clone https://github.com/sam220-hub/spidy-editor ~/.config/opencode/skills/spidy-editor
cd ~/.config/opencode/skills/spidy-editor
bash scripts/doctor.sh
python3 scripts/library_restore.py
```

On Windows:

```powershell
git clone https://github.com/sam220-hub/spidy-editor "$env:USERPROFILE\.config\opencode\skills\spidy-editor"
cd "$env:USERPROFILE\.config\opencode\skills\spidy-editor"
python scripts\doctor.py
python scripts\library_restore.py
```

**Other agents** (untested; it is built with Claude Code). Codex, or any agent that reads Agent Skills: clone or symlink the folder into that agent's skills directory. Any other agent: tell it "Follow `<path>/spidy-editor/SKILL.md` to edit this recording." Every step is a plain shell command.
