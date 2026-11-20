<div align="center">

<h1>Spidy Editor</h1>

<p><b>Three minutes of you stumbling through a script in.<br>A 30-second reel that looks paid-for out.</b></p>

<p>An AI video editor skill for talking-head reels. Runs on Windows and macOS,<br>
in OpenCode, Claude Code, or any agent that reads <code>SKILL.md</code>.</p>

[![MIT](https://img.shields.io/badge/license-MIT-black?style=flat)](LICENSE)
[![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-black?style=flat)](#windows)
[![macOS](https://img.shields.io/badge/macOS-Apple%20silicon-black?style=flat)](#macos)

</div>

## What it does

Hand it one raw phone recording and it returns a finished 1080x1920 reel: the best take of every
sentence, the pauses removed, word-timed captions that never cover the face, motion scenes on the
spoken word, sound effects mixed against the voice, and a QA pass before anything is delivered.

Nothing on screen says anything the speaker did not say, and every step is deterministic: the cut
math, zoom tweens, caption placement, SFX levels and asset copying are scripts, not vibes. The
creative decisions stay with you (and the agent).

| step | what happens | command |
| --- | --- | --- |
| prep | phone clip → 1080x1920 / 30 fps, voice at -16 LUFS | `spidy prep IN.MOV $P` |
| transcription | word-level timestamps (Whisper) | `spidy transcribe $P/assets/talk.mp4 --out $P/build/words.whisper.json` |
| takes | picks the best take of each line, drops pauses | `spidy takes --script script.txt --words $P/build/islands.json --out $P/build/takes.json` |
| build | reel spec → `index.html`, caption groups, SFX table, warnings | `spidy build $P` |
| approve | a page with a frame at every cut | `spidy approval_sheet $P --open` |
| render | pinned HyperFrames renderer, Edge/Chrome on your PC | `spidy hf render -o build/reel.mp4` |
| finals | preview (720p) and final (1080p), plus a no-music version | `spidy finals preview $P --out $P/finals --code R12 --style "Clean OS" --title "..."` |
| QA | A/V lengths, loudness, SFX stem levels, contact sheet | `spidy qa $P $P/finals/"R12 - Clean OS.mp4"` |

## Install

### OpenCode

```powershell
git clone https://github.com/sam220-hub/spidy-editor "$env:USERPROFILE\.config\opencode\skills\spidy-editor"
```

On a PC that is all: the skill is discovered in `~/.config/opencode/skills/spidy-editor`, its ID is
`spidy-editor`, and `@spidy-editor` in a prompt loads it. If you already keep the folder somewhere
else, a junction works and avoids a second copy of the media library:

```powershell
cmd /c mklink /J "$env:USERPROFILE\.config\opencode\skills\spidy-editor" "D:\path\to\spidy-editor"
```

### Claude Code

```bash
git clone https://github.com/sam220-hub/spidy-editor ~/.claude/skills/spidy-editor
```

(`~/.agents/skills` is also read, by both OpenCode and Claude Code.)

### Then install the tools

```powershell
# Windows
winget install Gyan.FFmpeg Python.Python.3.12 OpenJS.NodeJS.LTS
python -m pip install numpy opencv-python pillow google-genai requests openai-whisper
setx PYTHONUTF8 1
```

```bash
# macOS
brew install ffmpeg node
python3 -m pip install numpy opencv-python pillow google-genai requests openai-whisper
```

```powershell
spidy doctor                    # 0 missing when you are done; "opt" lines are optional
spidy library                   # SFX, music beds and the emoji set (~60 MB)
```

Then just ask:

> Edit ~/Downloads/my-video.mov into a reel in Clean OS.

The agent reads [`SKILL.md`](SKILL.md), runs the steps, shows you the approval page, and renders.
A 60-second reel takes roughly 15–25 minutes of machine time.

## Styles

Named recipes (`recipes/`, described in [`docs/PLAYBOOK.md`](docs/PLAYBOOK.md)):

`Clean OS` · `Seoul list` · `RESULT` · `Face RESULT` · `stan style` · `vector explainer` ·
`POV montage` · `Whiteboard` · `Kinetic doc` · `Step Deck` · `Product page` · `Tactile paper` ·
`Caption News` · `News Package` · `Telestrator` · `Halftone Dossier` · `Swiss Grid` ·
`Data Story` · `Hologram HUD`

Plus seven one-word presets: `clean`, `editorial`, `meme`, `cinematic`, `launch`, `kinetic`, `pop`.

You can also point it at a reel you like — `make my video look like this` — and it studies the
reference and writes the plan.

## Windows

The whole pipeline runs natively: no Git Bash, no WSL, no build tools. [docs/WINDOWS.md](docs/WINDOWS.md)
has the command table and the honest differences:

- scripts run as `.py` (`python`, not `python3`); the `.sh` files are thin wrappers for macOS;
- `npx` is invoked as `node .../npm/bin/npx-cli.js`, because `cmd.exe` splits arguments with spaces;
- HyperFrames renders in the Edge/Chrome already installed instead of downloading its own;
- renders use the system ffmpeg (same picture, not byte-identical to a Mac render);
- the macOS Vision caption-size check is skipped (noted, not silent).

`spidy.cmd` finds a real Python even in a session that started before Python was installed, and
refreshes `PATH` from the registry so `node`, `npx` and `ffmpeg` are visible too.

## macOS

Apple silicon is what this codebase was built and tested on: MLX Whisper, VideoToolbox decode and the
macOS Vision caption check all work there. See [docs/INSTALL.md](docs/INSTALL.md).

## What you need

- 4 GB of disk for the toolchain; Whisper's default model is another ~1.5 GB on first use.
- A free [Gemini API key](https://aistudio.google.com/apikey) for the B-roll people/line check
  (frames go to Google). Without it that check is skipped and says so.
- An ElevenLabs key, only for the explainer's narrator.
- Music and SFX are downloaded at install time; the repo carries the manifests, not the media.

## Repository layout

```
SKILL.md            the agent's instructions (the skill itself)
scripts/            every step: prep, takes, build, render, finals, QA, library
recipes/            the named styles, one folder each
library/            manifests for SFX, music, memes, emoji, LUTs (media is downloaded)
templates/ styles/  reusable page and HTML building blocks
docs/               INSTALL, WINDOWS, PLAYBOOK, HOW-IT-WORKS, third-party licences
tests/              the checks the pipeline itself runs
```

## Credits

Spidy Editor is a renamed, Windows-hardened edition of
[ghost-editor](https://github.com/kurbaitaev/ghost-editor) by **kurbaitaev**, used and redistributed
under the MIT licence. The original copyright notice is kept in [LICENSE](LICENSE), and the editors,
recipes, styles and documentation are his work. The Windows port (native scripts, launcher, PATH and
encoding handling, docs) and the Spidy Editor packaging are the changes on top.

Demo reels, screenshots and the author's own footage belong to the original project — see it there
rather than here.

## Licence

MIT. Reels you make with it are yours.
