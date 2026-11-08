"""Download explicit YouTube or direct MP4 URLs and cache completed files."""
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from .config import home, ffmpeg

BROWSERS = ('edge','chrome','firefox','brave','chromium','opera','vivaldi','safari')


class YouTubeLoginRequired(RuntimeError):
    """The user must supply their own authenticated session or a local file."""


def cookie_options(browser: str | None = None, cookies: str | None = None) -> dict:
    """Translate explicit user options; never discover or load cookies by default."""
    if browser and cookies:
        raise ValueError('Choose --cookies-from-browser OR --cookies, not both.')
    if browser:
        name,_,profile=browser.partition(':')
        if name.lower() not in BROWSERS:
            raise ValueError('Supported browsers: '+', '.join(BROWSERS))
        return {'cookiesfrombrowser':(name.lower(),profile or None)}
    if cookies:
        path=Path(cookies).expanduser().resolve()
        if not path.is_file():
            raise ValueError('Cookie file does not exist. Supply a Netscape-format cookies.txt file.')
        return {'cookiefile':str(path)}
    return {}


class DownloadLogger:
    """Show downloader progress once; exceptions are reported by the CLI."""
    def debug(self,message):
        if not message.startswith('[debug]'):
            from rich.console import Console
            Console().print(message,markup=False)

    def warning(self,message):
        from rich.console import Console
        Console().print('Warning: '+message,style='yellow',markup=False)

    def error(self,message):
        pass


def javascript_runtimes() -> dict:
    """Enable an installed runtime supported by yt-dlp's YouTube extractor."""
    for name, minimum in [('deno',(2,3)),('node',(22,0))]:
        binary=shutil.which(name)
        if not binary:
            continue
        try:
            result=subprocess.run([binary,'--version'],capture_output=True,text=True,timeout=10)
            match=re.search(r'(\d+)\.(\d+)',result.stdout)
            if result.returncode==0 and match and tuple(map(int,match.groups()))>=minimum:
                return {name:{'path':binary}}
        except (OSError,subprocess.TimeoutExpired):
            continue
    raise RuntimeError('YouTube needs Node.js 22+ or Deno 2.3+. On Windows: winget install OpenJS.NodeJS.LTS; then reopen your terminal. Local MP4 files work without this.')


def download(url: str, cookies_from_browser: str | None = None, cookies: str | None = None) -> Path:
    parsed = urlparse(url)
    is_mp4=parsed.path.lower().endswith('.mp4')
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or (not is_mp4 and parsed.hostname not in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}):
        raise ValueError("Supply a YouTube URL, direct MP4 URL, or local video file.")
    if is_mp4 and (cookies_from_browser or cookies):
        raise ValueError('Cookie options apply only to YouTube links, not direct MP4 URLs.')
    authentication=cookie_options(cookies_from_browser,cookies)
    folder = home() / "cache" / hashlib.sha256(url.encode()).hexdigest()[:20]
    folder.mkdir(parents=True, exist_ok=True)
    marker = folder / "complete.json"
    if marker.exists():
        cached = folder / json.loads(marker.read_text())["file"]
        if cached.exists():
            return cached
    if is_mp4:
        import httpx
        from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn
        target=folder/'source.mp4'
        partial=folder/'source.mp4.part'
        try:
            with httpx.stream('GET',url,follow_redirects=True,timeout=60) as response:
                response.raise_for_status()
                total=int(response.headers['content-length']) if response.headers.get('content-length','').isdigit() else None
                with Progress(BarColumn(),DownloadColumn(),TransferSpeedColumn()) as progress, partial.open('wb') as stream:
                    task=progress.add_task('Downloading MP4',total=total)
                    for block in response.iter_bytes(1024*1024):
                        stream.write(block)
                        progress.update(task,advance=len(block))
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)
        marker.write_text(json.dumps({'file':target.name}))
        return target
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError
    try:
        with YoutubeDL({"outtmpl": str(folder / "source.%(ext)s"), "format": "bv*+ba/b", "merge_output_format": "mp4", "noplaylist": True, "ffmpeg_location": str(Path(ffmpeg()).parent), "js_runtimes": javascript_runtimes(), 'logger':DownloadLogger(), **authentication}) as ydl:
            info = ydl.extract_info(url, download=True)
            path = Path(ydl.prepare_filename(info))
    except DownloadError as exc:
        message=str(exc).lower()
        if any(term in message for term in ('not a bot','sign in','login required')):
            raise YouTubeLoginRequired('YouTube requires sign-in/verification. Open this video in your browser and complete it yourself. Then retry with --cookies-from-browser edge (or chrome/firefox/brave), or --cookies PATH_TO_COOKIES.txt. If YouTube still blocks it, use a local MP4. No cookies were automatically selected.') from exc
        if any(term in message for term in ('could not copy','decrypt','cookie database','failed to load cookies')):
            raise RuntimeError('Browser cookies could not be read. Close the selected browser and retry. If Windows encryption still prevents access, use Firefox, an explicitly exported cookies.txt file, or a local MP4. Do not share your cookie file.') from exc
        raise
    merged = folder / "source.mp4"
    if merged.exists():
        path = merged
    if not path.exists():
        raise RuntimeError("Download did not produce the expected file.")
    marker.write_text(json.dumps({"file": path.name}))
    return path
