# clipforge 0.4.0

**Clip → edit → save.** A CLI tool with an optional local visual template window for turning a YouTube link, direct MP4 link or local video into short MP4 clips. See the fonts and caption looks before choosing them, fit the full picture to your output shape, and generate English captions. There are no publishing, login, queue or scheduling commands. The picker is a native local window, with no web server or hosting.

## Quick start

```console
clipforge run "https://www.youtube.com/watch?v=VIDEO_ID"
clipforge run "C:\Users\Piyush\Videos\my-video.mp4"
clipforge run "https://example.com/video.mp4"
clipforge run --demo --clips 1
clipforge templates
clipforge run "C:\Videos\arabic-song.mp4" --templates --source-language ar --caption-language en --video-type lyrics
```

Use arrow keys + Enter for menus and Space to toggle clips. MP4s are saved to `clipforge-output/TIMESTAMP/` below your current directory; the final screen prints the exact paths. Use `--output` to choose another folder. Your input video is preserved.

## Visual fonts, themes and framing

`clipforge templates` opens the visual picker. Click a font sample or caption-look card to update the large preview. The **Framing & language** tab shows fitting templates and video shapes, plus source/caption language and audio-content settings. Press **Use these settings** to save them for the next run.

`clipforge run SOURCE` exports one clip automatically. Add `--templates` to choose a style using a frame from your video, or `--interactive` for the detailed terminal menus. The picker is local and requires Tkinter. On Linux install `python3-tk` if it is missing.

Choose a complete look with `--preset editorial` (4:5, Inter, mint accent), `--preset cinema` (16:9, Playfair Display, warm accent), or `--preset minimal` (9:16, Inter, white captions). Specific flags can refine a preset.

All 13 bundled fonts render from their actual font files. Theme previews are representative stills; final ASS captions animate in the exported video. You can save an offline reference sheet using `clipforge templates --preview-only --output templates.png`. Selections are remembered in `~/.clipforge/style.json`; explicit flags override saved choices when running without the picker. Inside the picker, your clicked choices take precedence.

### Fit the picture without cutting it off

With no saved layout, landscape footage uses a 4:5 Studio canvas. Portrait and square footage use a matching or nearby shape. Choose `--format 16:9`, `4:5`, `9:16`, or `1:1` to set the canvas yourself.

- `--framing studio`: inset full picture on a slate canvas, with captions positioned below the image.
- `--framing fit`: whole picture over a dark canvas; no face scan or subject crop.
- `--framing blur`: whole picture centered over a decorative blurred background; only the background copy is cropped.
- `--framing face`: deliberately fill the output using a face crop; choose this only if you want cropping. It falls back to the blurred full-picture layout if no face is detected.

Converting a landscape video to 9:16 while keeping the full picture necessarily leaves space above/below it. Fit modes fill that space instead of stretching or cutting the original image. 4:5 and 1:1 preserve the image the same way.

### Arabic lyrics → English captions

For Arabic songs choose **Caption language: English**, **Language actually spoken / sung: Arabic**, and **Audio content: Lyrics / singing** in the picker. Or use:

```console
clipforge run "C:\Videos\arabic-song.mp4" --source-language ar --caption-language en --video-type lyrics --framing fit
```

English output translates Arabic audio into English text using the local multilingual Whisper model; it does not simply label Arabic text as English. Lyrics mode disables the speech-only silence filter so singing is not discarded, and does not replace your lyrics with a visual narrative. Original audio is preserved unless you explicitly enable TTS.

English captions are the default for all new/saved templates unless you choose otherwise. Use `--caption-language original` to transcribe the source language instead. `--source-language auto` detects the audio language; `en` forces English when English audio has been misdetected. Source language and requested output language have separate cache entries, so older Arabic transcription results are not reused for English translation. Use multilingual `base`, `small` or `medium` models for translation, not a `.en` model. Larger models can improve difficult vocals but need more memory and processing time; set `whisper_model` in config.

Lyrics with loud music or unclear vocals can be mistranscribed or mistranslated. Translated word highlights have approximate timing because English and Arabic word order/length differ. Review the result and use caption corrections as needed. English captions are added over the video; existing Arabic text burned into the original picture remains visible.

## Installation on Windows

Python 3.11–3.13 is recommended; Python 3.12 was used for verification.

```powershell
winget install Python.Python.3.12
winget install Gyan.FFmpeg
```

Close the terminal and reopen it. Then:

```powershell
py -3.12 -m pip install --user pipx
py -3.12 -m pipx ensurepath
```

Close and reopen the terminal again. From the extracted package directory containing `pyproject.toml`:

```powershell
py -3.12 -m pipx install .
clipforge --version
clipforge doctor
```

To replace an older installed version with this local source:

```powershell
py -3.12 -m pipx install --force .
```

If using the built wheel, run `py -3.12 -m pipx install --force "FULL_PATH_TO\clipforge-0.4.0-py3-none-any.whl"` instead.

## macOS / Linux

Install ffmpeg with libass, H.264 and AAC support, and Python 3.11+:

```sh
# macOS
brew install ffmpeg python pipx
# Debian / Ubuntu
sudo apt update
sudo apt install ffmpeg python3 python3-venv pipx

# From this package directory:
pipx ensurepath
pipx install .
clipforge doctor
```

Alternatively install in a virtual environment: `python -m venv .venv`, activate it, then `python -m pip install .`. Use pipx if you want `clipforge` available from any terminal without activating an environment.

If ffmpeg is outside PATH, set `CLIPFORGE_FFMPEG` to the executable's absolute path. OpenCV is constrained to **4.x**, because OpenCV 5 removed the cascade detector this tool uses. A missing or empty face detector uses the blurred-background fallback. PyAV is constrained below version 19 to match the installed faster-whisper audio interface.

YouTube downloads need **Node.js 22+ or Deno 2.3+**; clipforge detects and enables an installed supported runtime automatically. On Windows, install Node with `winget install OpenJS.NodeJS.LTS`, then reopen your terminal. Local files and direct MP4 downloads do not need a JavaScript runtime. The Python package includes yt-dlp's `default` dependencies with its EJS support scripts. See the [official yt-dlp runtime setup guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS).

## Workflow

1. **Choose clips.** Supply a video link or file. Pick how many clips, a length range (20–30, 30–45 or 45–60 seconds), output aspect ratio (9:16, 4:5 or 1:1), and whether captions are on. AI selection uses your configured LLM to find engaging complete thoughts. Without an LLM key, clips are evenly spaced across the video, clearly labeled as unranked. Inspect the clip table and deselect unwanted clips.
2. **Edit and preview.** Use the font/theme selected in the visual picker, or choose them using terminal menus. Optionally correct caption text in your editor. On Windows, Notepad is used by default; save and close it to continue. A PNG preview is generated for each clip before the final render. `--open-preview` opens it in your default application.
3. **Save.** Confirm the previews. The tool renders H.264/AAC MP4s, prints their paths and saves an export manifest. Processing ends here.

Face scanning, reframing, preview creation and subtitle rendering have separate progress displays with elapsed time. A clip may take a minute or longer on a CPU; file size, video length and hardware affect processing time. Ctrl+C stops processing and preserves completed files.

Only use videos you own or have permission to edit. The first run displays a reminder.

## Editing controls and examples

```powershell
# Local file, normal menus:
clipforge run "C:\Videos\podcast.mp4"

# Export to a specific folder:
clipforge run "C:\Videos\podcast.mp4" --output "C:\Videos\Finished Clips"

# One explicit trim: start at 90 seconds, save the next 30 seconds:
clipforge run "C:\Videos\podcast.mp4" --start 90 --duration 30

# No API key: select three evenly spaced clips, with speech captions:
clipforge run "C:\Videos\podcast.mp4" --yes --selection even --clips 3 --length 20-30 --theme "Neon Glow" --font Anton

# No captions or transcription/model download; just trim, reframe and save:
clipforge run "C:\Videos\podcast.mp4" --yes --start 90 --duration 30 --captions off --selection even --format 1:1

# Edit captions in Notepad, then preview:
clipforge run "C:\Videos\podcast.mp4" --edit-captions --open-preview

# Keep only chosen clips in unattended mode:
clipforge run "https://youtu.be/VIDEO_ID" --yes --selection even --clips 3 --keep 1,3

clipforge --help
clipforge run --help
clipforge doctor
```

`--local-video PATH` remains an alias for supplying the path positionally. Put paths containing spaces inside quotes. `--start` is measured in seconds, creates one clip, and accepts `--duration` between 20 and 60 seconds; it must fit inside the source. It bypasses AI selection. `--selection even` distributes non-overlapping clips across the video. If the source is too short for the requested count/length, reduce either option.

The default run exports one 20–30 second clip with English captions and uses your saved style or Editorial defaults. Selection uses AI when an LLM key is configured, otherwise evenly spaced selection. Use `--clips` to export more, or `--captions off` for a clean video. `--yes` remains an alias for the default automatic mode.

### Caption corrections

Caption editing opens a text file with short phrases, one per line. Correct words **without adding or removing lines**; a blank line removes that phrase. Save and close the editor. Unchanged phrases retain the original word timestamps; changed phrases spread their words across the original phrase interval. This keeps later phrases from shifting but corrected words have approximate timing. Caption text editing is optional.

On macOS/Linux set `EDITOR` or `VISUAL` (e.g. `export EDITOR=nano`). On Windows the default is Notepad; you can set `$env:EDITOR = 'notepad.exe'` in PowerShell. Editors that start a separate process must wait for the file to close, e.g. `code --wait`.

### Themes and fonts

Themes: Classic White, Yellow Pop, Neon Glow, Minimal Black Box, Gradient Karaoke, Comic Bold, Cinematic Lower-Third, Hormozi-style. ASS approximates Gradient Karaoke with timed color transitions.

All 13 fonts and upstream license texts are included: Montserrat, Poppins, Bebas Neue, Anton, Oswald, Bangers, Roboto Condensed, Inter, Playfair Display, Lobster, Luckiest Guy, Archivo Black and Permanent Marker.

Speech and lyric captions highlight the current word in short groups. `--video-type speech`, `lyrics` or `non-speech` overrides automatic transcript-density detection. With an LLM key, non-speech mode samples frames and creates a short factual narrative, in English when English captions are selected. Without a key it keeps available transcript captions; a silent video can have no captions. Use `lyrics` for sung vocals rather than visual narratives. Use `--captions off` for a clean export without subtitles.

Optional `--tts` replaces source audio with a local voiceover of the caption text. Install it with `pipx inject clipforge pyttsx3`; Linux may also require `espeak-ng`. The voice is padded/truncated to the clip length and captions are not force-aligned to synthesized speech. Text must be available and captions must be on.

## Optional AI and configuration

**No account or API key is required** for manual/evenly spaced selection with local speech captions. The first real transcription downloads a faster-whisper model; later runs use the local model cache. The demo uses synthetic captions and never downloads a model.

AI highlight selection and visual narratives require an LLM key. Copy `.env.example` to `.env` in the directory from which you run the command:

```dotenv
LLM_API_KEY=your-key
LLM_BASE_URL=https://api.openai.com/v1
```

Preferences live in `~/.clipforge/config.toml`:

```toml
model = "gpt-4o-mini"
whisper_model = "base"
```

The provider adapter is `clipforge/llm.py`. Change the model and base URL for another OpenAI-compatible JSON endpoint, or replace `LLM.json()` for another provider. Non-speech narrative requires a vision-capable model. Transcripts and sampled frames are sent to the provider when the corresponding AI feature is used. Protect your `.env` and private media; `.env` is excluded from version control.

`CLIPFORGE_HOME` overrides the state/cache directory. Completed downloads and transcripts are cached so reruns avoid repeating work. Legacy timezone and LinkedIn fields in an existing config are ignored; there is no need to supply them or log in.

## Saved files

- `clip-1.mp4`: finished video to use or share yourself.
- `preview-1.png`: preview frame.
- `clip-1.ass`: editable ASS subtitle source.
- `clip-1-raw.mp4`: reframed clip before subtitle burn-in.
- `clip-1-captions.txt`: caption correction text, when editing was selected.
- `manifest.json`: clip timestamps, title, style, word timestamps and saved paths.

The demo also saves its generated `sample.mp4`. Optional voiceover creates a WAV and voiced intermediate video. Existing files with generated names in an explicitly reused output directory are overwritten; use a new folder if you want to keep earlier exports. The default uses a fresh timestamped folder. Export refuses a folder/name combination that would overwrite the source video.

## Offline demo

```console
clipforge run --demo --clips 1
clipforge run --demo --yes --start 0 --duration 20 --theme "Neon Glow" --font Anton
```

The demo generates a 65-second test-pattern video with tone audio and synthetic captions. It uses real reframing, ASS rendering, PNG previewing and local saving. It does not call an LLM. The first command uses the normal menus; the second exports one 20-second clip automatically.

## Limits and troubleshooting

### YouTube asks you to sign in or confirm you are not a bot

Open the video in your own browser, sign in yourself and complete any verification YouTube shows. Then explicitly choose that signed-in browser for the download:

```powershell
clipforge run "https://www.youtube.com/watch?v=VIDEO_ID" --cookies-from-browser edge --templates
# Other supported browsers include chrome, firefox and brave.
# For a specific browser profile:
clipforge run "https://www.youtube.com/watch?v=VIDEO_ID" --cookies-from-browser "edge:Profile 1"
# Or use your own exported Netscape-format cookie file:
clipforge run "https://www.youtube.com/watch?v=VIDEO_ID" --cookies "C:\Private\cookies.txt"
```

Cookie loading is opt-in: Clipforge never automatically reads a browser session or exports cookies, and does not save cookie contents in style settings, manifests or the clip cache. yt-dlp handles the selected browser/file. `--cookies` and `--cookies-from-browser` are mutually exclusive and apply only to YouTube, never direct MP4 hosts or local files. Browser profile selection follows `BROWSER:PROFILE`, for example `edge:Profile 1`.

If Windows locks the browser cookie database, close that browser and retry. Some Chromium browser encryption can prevent extraction even after closing it; use a Firefox session, your own exported cookie file, or a permissioned local MP4 instead. Do not send or share cookie files: they contain session credentials. Signing in does not guarantee access if YouTube continues to restrict the request. Clipforge does not automate sign-in, verification or bypass those restrictions.

See yt-dlp's [official cookie instructions](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp) and [YouTube-specific notes](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies).

- Downloading requires internet access. YouTube restrictions and yt-dlp site changes can prevent downloads. A direct MP4 URL must have a path ending in `.mp4` (a query string is allowed). Authenticated YouTube access requires an explicitly supplied browser session or cookie file. DRM is not handled.
- CPU transcription and 1080-pixel exports can take time. The Whisper model requires a download on first use. Captions off plus manual/even selection skips transcription entirely.
- Even selection does not look for complete thoughts. AI choices are estimates and may need manual trimming with `--start`/`--duration`.
- Optional face cropping uses the largest frontal face, not active-speaker identification. Multiple speakers and rapid cuts can produce imperfect crops. Default Fit preserves the full picture and never invokes face cropping.
- Very long transcripts may exceed your provider's context window. Model narrative and captions need review; sampled frames can miss brief events. Font language coverage varies.
- If the command is not recognized, run `py -3.12 -m pipx ensurepath`, close the terminal, and reopen it. For missing ffmpeg, check `ffmpeg -version` and restart your terminal after installing it.
- Run `clipforge doctor` to check local dependencies and bundled fonts. It does not make paid API calls.
- Hugging Face's unauthenticated-download warning is informational: the public Whisper model needs no token, but anonymous downloads can be rate-limited. Windows can cache model files by copying them rather than using symlinks. Clipforge suppresses the symlink warning; you do not need to run as administrator or enable Developer Mode.
- If you see `open() got an unexpected keyword argument 'metadata_errors'`, update to this build: it pins a compatible PyAV version. Upstream [faster-whisper audio decoding](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/audio.py) documents that PyAV 19 removed that option.

## Development

```sh
python -m pip install ".[test]"
python -m pytest -q
```

`cli.py` owns the wizard; `gallery.py` provides the native template picker; `download.py`, `transcribe.py`, `clip_select.py` and `reframe.py` prepare clips; `editing.py` corrects captions; `themes.py` and `subtitles.py` render them; `narrative.py` handles optional vision/TTS. `fonts/` contains the bundled assets. See `VERIFICATION.md` for checks performed on this build.
