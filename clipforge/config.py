"""Persistent preferences, environment secrets, and binary discovery."""
import os
import shutil
import subprocess
import tomllib
import tempfile
from pathlib import Path


def home() -> Path:
    path = Path(os.environ.get("CLIPFORGE_HOME", "~/.clipforge")).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings() -> dict:
    from dotenv import load_dotenv
    load_dotenv()
    path = home() / "config.toml"
    if not path.exists():
        path.write_text('model = "gpt-4o-mini"\nwhisper_model = "base"\n', encoding="utf-8")
    return tomllib.loads(path.read_text(encoding="utf-8"))


def ffmpeg() -> str:
    binary = os.environ.get("CLIPFORGE_FFMPEG") or shutil.which("ffmpeg")
    if not binary:
        raise RuntimeError("ffmpeg is missing. Install it and add it to PATH, or set CLIPFORGE_FFMPEG.")
    return binary


def command(args: list[str], duration: float | None = None, title: str = "Processing video") -> None:
    if duration is not None:
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
        with tempfile.TemporaryFile(mode="w+b") as errors:
            process = subprocess.Popen([args[0], "-progress", "pipe:1", "-nostats", *args[1:]], stdout=subprocess.PIPE, stderr=errors, text=True, encoding="utf-8", errors="replace")
            try:
                with Progress(SpinnerColumn(), TextColumn("{task.description}"), BarColumn(), TaskProgressColumn(), TimeElapsedColumn()) as progress:
                    task=progress.add_task(title,total=max(.01,duration))
                    for line in process.stdout:
                        key,_,value=line.strip().partition('=')
                        if key=='out_time_us':
                            try: progress.update(task,completed=min(duration,max(0,int(value)/1_000_000)))
                            except ValueError: pass
                    code=process.wait()
                    if code==0: progress.update(task,completed=duration)
                if code:
                    errors.seek(max(0,errors.tell()-4000))
                    raise RuntimeError(f"{Path(args[0]).name} failed:\n{errors.read().decode('utf-8',errors='replace')}")
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                process.stdout.close()
        return
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(f"{Path(args[0]).name} failed:\n{result.stderr[-4000:]}")
