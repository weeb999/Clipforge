# Clipforge

Create captioned short clips with a browser editor or a Python CLI.

**Live website:** https://clipforge-the-next-step.netlify.app/

## Browser editor

The `web/dist` directory contains the deployed, static website. It includes:

- Local video upload and trimming.
- 9:16, 4:5, 1:1, and 16:9 output formats.
- Full-picture and editorial layouts.
- Editorial, Cinema, and Minimal caption presets, with 13 bundled fonts.
- English captions and translation from Arabic audio, processed in the browser.
- Local MP4 or WebM export, depending on browser support.
- Responsive layouts for desktop, tablet, and phone screens.

### Run locally

```sh
python -m http.server 8000 --directory web/dist
```

Open http://localhost:8000. Speech processing downloads a model on first use and requires internet access. Keep the tab open during export. Captions and translated timings should be reviewed, particularly for singing.

### Deploy to Netlify

Import this repository into Netlify, leave the build command empty, and set the publish directory to `web/dist`. Alternatively, set the base directory to `web` to use its `netlify.toml`.

If deploying under another address, update the canonical URL in `web/dist/index.html`, plus `web/dist/robots.txt` and `web/dist/sitemap.xml`. Replace the Google verification tag with your own if needed.

The browser version accepts local files. YouTube URL importing requires a processing service and is not implemented in this static editor. Export capabilities depend on the browser and device.

## Python CLI

Python 3.11 or later and FFmpeg are required.

```sh
python -m pip install .
clipforge --help
clipforge run --demo --clips 1
clipforge run "path/to/video.mp4"
```

The CLI also supports YouTube URLs, local templates, transcription, and rendering through FFmpeg. See [CLI.md](CLI.md) for installation, configuration, options, and troubleshooting. Copy `.env.example` to `.env` to configure optional LLM access. Never commit API keys or browser cookies.

## Tests

```sh
python -m pip install '.[test]'
python -m pytest
```

## Responsible use

Only use videos you own or have permission to edit and repost. This project edits and saves clips; it does not publish to social platforms or schedule posts.

## Fonts

Font files and their license notices are included alongside the assets in `clipforge/fonts` and `web/dist/fonts`. Preserve those notices when redistributing the fonts.
