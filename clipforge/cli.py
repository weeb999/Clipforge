"""Terminal-only video selection, caption editing and local export."""
import argparse
import json
import os
import subprocess
import sys
import webbrowser
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from . import __version__
from .config import settings, home, ffmpeg
from .themes import THEMES, FONTS

console = Console(highlight=False)


def choose(message: str, choices: list, default=None):
    import questionary
    answer = questionary.select(message, choices=choices, default=default).ask()
    if answer is None:
        raise KeyboardInterrupt
    return answer


def confirm(message: str) -> bool:
    return choose(message, ['Yes', 'No']) == 'Yes'


def table(title: str, columns: list[str], rows: list) -> None:
    result = Table(title=title)
    for column in columns:
        result.add_column(column)
    for row in rows:
        result.add_row(*(str(value) for value in row))
    console.print(result)


def resolve_source(source: str | None, local_video: str | None, cookies_from_browser: str | None = None, cookies: str | None = None) -> Path:
    """Accept a positional video URL or local path, including Windows paths."""
    if source and local_video:
        raise ValueError('Provide a link/file OR --local-video, not both.')
    value = local_video or source
    if not value:
        raise ValueError('Supply a YouTube link, a local MP4 path, or --demo.')
    if value.lower().startswith(('https://', 'http://')) and not local_video:
        from .download import download
        return download(value,cookies_from_browser=cookies_from_browser,cookies=cookies)
    if cookies_from_browser or cookies:
        raise ValueError('Cookie options apply only to YouTube links.')
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f'Video file does not exist: {path}')
    return path


def run(args) -> None:
    from .transcribe import transcribe
    from .clip_select import select, evenly_spaced, manual_clip
    from .reframe import probe, cut, FORMATS
    from .subtitles import generate, render
    from .llm import LLM
    from .editing import edit_captions
    from .gallery import load_style, choose_style
    from .reframe import FRAMING, studio_caption_margin
    config = settings()
    interactive = args.interactive and not args.yes
    if interactive and not sys.stdin.isatty():
        raise ValueError('Interactive mode needs a terminal. Use --yes and flags for unattended runs.')
    if args.demo and (args.source or args.local_video):
        raise ValueError('Use --demo without a link or local video.')
    if args.demo and (args.cookies_from_browser or args.cookies):
        raise ValueError('Demo mode does not use browser cookies.')
    if args.duration is not None and args.start is None:
        raise ValueError('--duration requires --start.')
    if args.start is not None and args.clips not in (None, 1):
        raise ValueError('Manual --start creates one clip; use --clips 1.')
    if not args.demo and not (args.source or args.local_video):
        raise ValueError('Supply a YouTube link, a local MP4 path, or --demo.')
    notice = home() / 'rights-acknowledged'
    if not notice.exists():
        console.print(Panel('Only use videos you own or have permission to edit.'))
        if interactive and not confirm('Do you own this video or have permission to edit it?'):
            return
        notice.touch()
    ffmpeg()
    folder = Path(args.output or (Path.cwd() / 'clipforge-output' / datetime.now().strftime('%Y%m%d-%H%M%S-%f'))).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    if args.demo:
        from .demo import sample
        source, words = sample(folder)
        console.print('DEMO: local test video, tone audio and synthetic captions.')
    else:
        with console.status('Preparing video…'):
            source = resolve_source(args.source, args.local_video, args.cookies_from_browser, args.cookies)
    duration, source_width, source_height = probe(source)
    if duration < 20:
        raise ValueError('Source must be at least 20 seconds long.')
    style = load_style((source_width, source_height))
    if args.preset:
        from .gallery import PRESETS
        style.update(PRESETS[args.preset])
    visual = args.templates
    if visual:
        initial={key:getattr(args,key) for key in style if getattr(args,key,None) is not None}
        picked=choose_style({**style,**initial}, source=source)
        if picked is None:
            raise KeyboardInterrupt
        style=picked
    count = 1 if args.start is not None else args.clips or (int(choose('How many clips?', ['1', '2', '3', '5'])) if interactive else 1)
    lengths = args.length or (choose('Clip length in seconds?', ['20-30', '30-45', '45-60']) if interactive else '20-30')
    minimum, maximum = map(int, lengths.split('-'))
    aspect = style['format'] if visual else args.format or (choose('Output format?', list(FORMATS),default=style['format']) if interactive else style['format'])
    framing = style['framing'] if visual else args.framing or (choose('Picture fitting? (Fit preserves the entire picture)', list(FRAMING),default=style['framing']) if interactive else style['framing'])
    caption_language = style['caption_language'] if visual else args.caption_language or style['caption_language']
    source_language = style['source_language'] if visual else args.source_language or style['source_language']
    video_mode = style['video_type'] if visual else args.video_type or style['video_type']
    captions = args.captions or (choose('Captions?', ['on', 'off']) if interactive else 'on')
    has_key = bool(os.getenv('LLM_API_KEY') or os.getenv('OPENAI_API_KEY'))
    selection = args.selection
    if selection is None:
        selection = choose('Clip selection?', ['ai', 'even']) if interactive and has_key and not args.demo and args.start is None else ('ai' if has_key else 'even')
    if selection == 'ai' and not has_key and not args.demo and args.start is None:
        raise ValueError('AI selection requires LLM_API_KEY. Use --selection even or --start instead.')
    llm = LLM(config['model'])
    console.print(Panel('Step 1 · Choose your clips'))
    if not args.demo:
        with console.status('Preparing captions…'):
            words = transcribe(source, config['whisper_model'],source_language=source_language,caption_language=caption_language,vad_filter=video_mode!='lyrics') if captions == 'on' or (selection == 'ai' and args.start is None) else []
    coverage = sum(max(0, w['end'] - w['start']) for w in words) / duration
    detected = 'speech' if len(words) / duration > .35 and coverage > .15 else 'non-speech'
    kind = video_mode if video_mode!='auto' else (choose(f'Detected {detected}; caption mode?', list(dict.fromkeys([detected,'speech','lyrics','non-speech']))) if interactive and captions == 'on' else detected)
    if kind=='lyrics' and video_mode!='lyrics' and not args.demo:
        with console.status('Transcribing vocals with lyrics mode…'):
            words=transcribe(source,config['whisper_model'],source_language=source_language,caption_language=caption_language,vad_filter=False)
    if args.start is not None:
        clips = [manual_clip(args.start, args.duration if args.duration is not None else minimum, duration)]
    elif args.demo or selection == 'even':
        clips = evenly_spaced(duration, count, minimum, maximum)
        console.print('Evenly spaced selection: review cut points; these are not AI-ranked highlights.')
    else:
        with console.status('Choosing complete, engaging segments…'):
            images = None
            if kind == 'non-speech':
                from .narrative import sample_frames
                images = sample_frames(source, 0, duration, count=12)
            clips = select(llm, words, duration, count, minimum, maximum, images)
    table('Picked clips', ['#', 'Start', 'End', 'Score', 'Title'], [(i + 1, f'{c.start:.2f}', f'{c.end:.2f}', c.score if selection == 'ai' and not args.demo and args.start is None else '—', c.hook) for i, c in enumerate(clips)])
    if interactive:
        import questionary
        kept = questionary.checkbox('Keep clips (Space toggles, Enter continues)', choices=[questionary.Choice(c.hook, value=i, checked=True) for i, c in enumerate(clips)]).ask()
        if kept is None:
            raise KeyboardInterrupt
        clips = [c for i, c in enumerate(clips) if i in kept]
    elif args.keep:
        keep = {int(value) for value in args.keep.split(',')}
        if not keep or not keep <= set(range(1, len(clips) + 1)):
            raise ValueError('--keep must contain valid clip numbers from the table.')
        clips = [c for i, c in enumerate(clips, 1) if i in keep]
    if not clips:
        raise ValueError('No clips selected.')
    generated={folder / f'clip-{i}{suffix}.mp4' for i in range(1,len(clips)+1) for suffix in ('','-raw','-voiced')}
    if source.resolve() in generated:
        raise ValueError('Choose a different --output folder to avoid overwriting your source video.')
    console.print(Panel('Step 2 · Edit and preview'))
    theme = style['theme'] if visual else args.theme or (choose('Caption theme?', list(THEMES),default=style['theme']) if interactive and captions == 'on' else style['theme'])
    font = style['font'] if visual else args.font or (choose('Caption font?', FONTS,default=style['font']) if interactive and captions == 'on' else style['font'])
    console.print(f'Exporting {aspect} · {FRAMING[framing]} · {theme} / {font}', markup=False)
    dimensions = FORMATS[aspect]
    caption_margin = studio_caption_margin(*dimensions, (source_width, source_height)) if framing == 'studio' else None
    if args.tts and captions == 'off':
        raise ValueError('--tts requires captions on.')
    if captions == 'on' and kind == 'non-speech' and not has_key and not args.demo:
        console.print('No LLM key: keeping available transcript captions; visual narrative is disabled.')
    tts = args.tts or (interactive and captions == 'on' and kind == 'non-speech' and confirm('Add local TTS voiceover?'))
    prepared = []
    for index, clip in enumerate(clips, 1):
        console.print(f'Preparing clip {index}/{len(clips)}')
        raw = folder / f'clip-{index}-raw.mp4'
        cut(source, clip, raw, aspect,framing=framing)
        caption_words = [w for w in words if w['end'] > clip.start and w['start'] < clip.end] if captions == 'on' else []
        if captions == 'on' and kind == 'non-speech' and has_key and not args.demo:
            from .narrative import narrate
            caption_words = narrate(llm, source, clip.start, clip.end,caption_language=caption_language)
        if captions == 'on' and (args.edit_captions or (interactive and caption_words and confirm(f'Edit captions for clip {index} in your text editor?'))):
            caption_words = edit_captions(caption_words, folder / f'clip-{index}-captions.txt')
        if tts:
            if not caption_words:
                raise ValueError('TTS needs transcript or narrative text for this clip.')
            from .narrative import voiceover
            voiced = folder / f'clip-{index}-voiced.mp4'
            voiceover(raw, caption_words, voiced)
            raw = voiced
        ass = folder / f'clip-{index}.ass'
        ass.write_text(generate(caption_words, clip.start, clip.end, theme, font, *dimensions, narrative=kind == 'non-speech', caption_margin=caption_margin), encoding='utf-8')
        output = folder / f'clip-{index}.mp4'
        preview = folder / f'preview-{index}.png'
        if interactive or args.open_preview:
            render(raw, ass, output, preview, preview_only=True)
            console.print(f'Preview: {preview}', markup=False)
        if args.open_preview:
            webbrowser.open(preview.as_uri())
        prepared.append((clip, raw, ass, output, preview, caption_words))
    if interactive and not confirm('Save these previews as final MP4 clips?'):
        console.print(f'Previews and working files saved in {folder}', markup=False)
        return
    console.print(Panel('Step 3 · Save clips'))
    manifest = []
    for clip, raw, ass, output, preview, caption_words in prepared:
        render(raw, ass, output, preview)
        console.print(f'Saved MP4: {output}', markup=False)
        manifest.append({**asdict(clip), 'video': str(output), 'preview': str(preview), 'subtitles': str(ass), 'theme': theme, 'font': font, 'format': aspect, 'framing':framing,'caption_language':caption_language,'source_language':source_language,'video_type':kind,'captions': captions, 'words': caption_words})
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    table('Saved clips', ['Title', 'MP4 file'], [(row['hook'], row['video']) for row in manifest])
    console.print(f'Done. Saved {len(manifest)} clips to {folder}', markup=False)


def doctor() -> None:
    import importlib.util
    checks = []
    try:
        result = subprocess.run([ffmpeg(), '-filters'], capture_output=True, text=True)
        checks.append(('ffmpeg + ASS', 'OK' if ' ass ' in result.stdout else 'Missing libass support'))
    except RuntimeError as exc:
        checks.append(('ffmpeg', str(exc)))
    for module in ['yt_dlp', 'faster_whisper', 'cv2', 'questionary','PIL','tkinter']:
        checks.append((module, 'OK' if importlib.util.find_spec(module) else 'Missing'))
    try:
        from .download import javascript_runtimes
        checks.append(('YouTube JavaScript', ', '.join(javascript_runtimes())+' enabled'))
    except RuntimeError as exc:
        checks.append(('YouTube JavaScript',str(exc)))
    checks.append(('LLM key', 'Present (AI selection available)' if os.getenv('LLM_API_KEY') or os.getenv('OPENAI_API_KEY') else 'Optional; evenly spaced/manual clips work without a key'))
    checks.append(('Bundled fonts', str(len(list((Path(__file__).parent / 'fonts').glob('*.ttf'))))))
    table('Clipforge doctor', ['Check', 'Result'], checks)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog='clipforge', description='Clip, edit and save videos locally from a YouTube link, MP4 link or local file.')
    p.add_argument('--version', action='version', version=f'clipforge {__version__}')
    sub = p.add_subparsers(dest='command', required=True)
    r = sub.add_parser('run', help='Choose clips, edit captions and save MP4 files')
    r.add_argument('source', nargs='?', help='YouTube URL, direct MP4 URL or local video path')
    r.add_argument('--local-video', help='Alternative way to supply a local video path')
    auth=r.add_mutually_exclusive_group()
    auth.add_argument('--cookies-from-browser',metavar='BROWSER[:PROFILE]',help='Explicitly use your signed-in browser session: edge, chrome, firefox or brave')
    auth.add_argument('--cookies',metavar='FILE',help='Use your own Netscape-format YouTube cookie file; never share it')
    r.add_argument('--demo', action='store_true')
    r.add_argument('--clips', type=int, choices=range(1, 11))
    r.add_argument('--length', choices=['20-30', '30-45', '45-60'])
    r.add_argument('--start', type=float, help='Manual start time in seconds; makes one clip')
    r.add_argument('--duration', type=float, help='Manual clip duration, 20–60 seconds')
    r.add_argument('--selection', choices=['ai', 'even'], help='Defaults to AI with a key, otherwise evenly spaced')
    from .gallery import PRESETS
    from .reframe import FORMATS, FRAMING
    r.add_argument('--format', choices=list(FORMATS))
    r.add_argument('--framing', choices=list(FRAMING), help='Choose a picture layout')
    r.add_argument('--preset', choices=list(PRESETS), help='Apply a complete layout and caption style')
    r.add_argument('--caption-language',choices=['en','original'],help='English captions by default; translates other spoken languages')
    r.add_argument('--source-language',help='Actual audio language: auto, en, ar, hi, etc. Force en if English is misdetected')
    r.add_argument('--templates',action='store_true',help='Open the visual font/theme/framing picker before processing')
    r.add_argument('--keep', help='Comma-separated clip numbers to keep')
    r.add_argument('--captions', choices=['on', 'off'])
    r.add_argument('--theme', choices=list(THEMES))
    r.add_argument('--font', choices=FONTS)
    r.add_argument('--video-type', choices=['auto','speech','lyrics','non-speech'],help='Use lyrics for singing; preserves vocals instead of generating a visual narrative')
    r.add_argument('--tts', action='store_true')
    r.add_argument('--edit-captions', action='store_true', help='Correct caption text in EDITOR/VISUAL')
    r.add_argument('--open-preview', action='store_true')
    r.add_argument('--output', help='Folder for saved clips (default: ./clipforge-output/TIMESTAMP)')
    interaction = r.add_mutually_exclusive_group()
    interaction.add_argument('--interactive', action='store_true', help='Walk through the detailed terminal menus')
    interaction.add_argument('--yes', action='store_true', help='Use flags/defaults and save without prompts (already the default)')
    sub.add_parser('doctor', help='Check video tools, fonts and optional AI configuration')
    gallery=sub.add_parser('templates',help='Open the visual font, caption and framing templates')
    gallery.add_argument('--preview-only',action='store_true',help='Save a PNG reference sheet without opening a window')
    gallery.add_argument('--output',help='Reference-sheet path (with --preview-only)')
    return p


def main() -> None:
    args = parser().parse_args()
    try:
        settings()
        if args.command == 'run':
            run(args)
        elif args.command == 'templates':
            from .gallery import choose_style,contact_sheet
            if args.preview_only:
                path=contact_sheet(Path(args.output).resolve() if args.output else home()/'templates.png')
                console.print(f'Template reference: {path}',markup=False)
            else:
                selected=choose_style()
                if selected:
                    console.print('Template saved. Your next clipforge run will use these settings.')
        else:
            doctor()
    except KeyboardInterrupt:
        console.print('\nStopped. Any completed files remain in the output folder.')
        raise SystemExit(130)
    except Exception as exc:
        console.print(f'Error: {exc}', style='red', markup=False)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
