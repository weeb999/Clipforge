"""Word-highlight ASS captions and ffmpeg rendering."""
from pathlib import Path
from .config import command, ffmpeg
from .themes import THEMES


def timestamp(seconds: float) -> str:
    cs = max(0, round(seconds * 100))
    return f"{cs//360000}:{cs//6000%60:02d}:{cs//100%60:02d}.{cs%100:02d}"


def escape(text: str) -> str:
    # Strip control characters and escape ASS override delimiters.
    return "".join(c for c in text if c >= " ").replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def generate(words: list[dict], start: float, end: float, theme: str, font: str, width: int, height: int, narrative: bool = False, caption_margin: float | None = None) -> str:
    t = THEMES[theme]
    size = round(width * (.045 if t.animation == 'steady' else .057))
    margin = round(height * (.15 if caption_margin is None else caption_margin))
    alignment = t.alignment if caption_margin is None else 2
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{size},{t.color},{t.highlight},{t.outline_color},&H90000000,-1,0,0,0,100,100,0,0,{3 if t.box else 1},{t.stroke},{t.shadow},{alignment},70,70,{margin},1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    selected = [w for w in words if float(w["end"]) > start and float(w["start"]) < end]
    events = []
    groups=[selected[i:i+3] for i in range(0,len(selected),3)]
    if len(groups)>1 and len(groups[-1])==1:
        groups[-2].extend(groups.pop())
    for group in groups:
        for current, word in enumerate(group):
            begin = max(start, float(word["start"])) - start
            stop = min(end, float(word["end"])) - start
            if stop <= begin:
                continue
            animation = {"steady": "", "fade": r"{\fad(40,40)}", "pop": r"{\fscx108\fscy108\t(0,100,\fscx100\fscy100)}", "glow": r"{\blur2\t(0,120,\blur0.6)}", "gradient": r"{\t(0,180,\1c&HFF66FF&)}", "slide": f"{{\\move({width//2},{height-margin+20},{width//2},{height-margin},0,160)}}"}[t.animation]
            parts = []
            for index, item in enumerate(group):
                color = t.highlight if index == current and not narrative else t.color
                parts.append(f"{{\\1c{color}&}}{escape(item['word'])}")
            events.append(f"Dialogue: 0,{timestamp(begin)},{timestamp(stop)},Default,,0,0,0,,{animation}{' '.join(parts)}\n")
    return header + "".join(events)


def filter_path(path: Path) -> str:
    # libavfilter quoting is distinct from shell quoting, including on Windows.
    return str(path.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"'\''").replace("[", r"\[").replace("]", r"\]")


def render(source: Path, ass: Path, output: Path, preview: Path, preview_only: bool = False) -> None:
    fonts = Path(__file__).parent / "fonts"
    vf = f"ass=filename='{filter_path(ass)}':fontsdir='{filter_path(fonts)}'"
    command([ffmpeg(), "-y", "-i", str(source), "-ss", "1", "-vf", vf, "-frames:v", "1", "-update", "1", str(preview)],duration=1,title="Generating preview")
    if preview_only:
        return
    from .reframe import probe
    command([ffmpeg(), "-y", "-i", str(source), "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output)],duration=probe(source)[0],title="Burning captions")
