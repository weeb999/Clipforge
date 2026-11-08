"""Generate an offline fixture with a known, synthetic transcript."""
from pathlib import Path
from .config import command, ffmpeg


def sample(folder: Path) -> tuple[Path, list[dict]]:
    video = folder / "sample.mp4"
    if not video.exists():
        command([ffmpeg(), "-y", "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=24", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100", "-t", "65", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", str(video)])
    text = ("This is a synthetic demo caption track. Small consistent improvements create lasting results. Start with one clear goal and measure what changes. Review the evidence and share what you learned with your team. " * 6).split()
    words = [{"word": w, "start": i * .32, "end": (i + 1) * .32} for i, w in enumerate(text) if (i+1)*.32 <= 65]
    return video, words
