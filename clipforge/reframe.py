"""Sample a face track and reframe; use a blurred canvas when no face is found."""
from pathlib import Path
from .config import command, ffmpeg

FORMATS = {"9:16": (1080, 1920), "4:5": (1080, 1350), "1:1": (1080, 1080), "16:9": (1920, 1080)}
FRAMING = {
    'studio': 'Studio canvas',
    'fit': 'Full picture',
    'blur': 'Soft background',
    'face': 'Face crop',
}
STUDIO_BACKGROUND = '111923'
STUDIO_CAPTION_MARGIN = .09


def studio_region(width: int, height: int) -> tuple[int, int, int]:
    """Return the inset picture area's width, height and vertical center."""
    return round(width * .92), round(height * .72), round(height * .42)


def studio_caption_margin(width: int, height: int, source_size: tuple[int, int]) -> float:
    """Position captions below the fitted image with room for a second line."""
    region_width, region_height, center = studio_region(width, height)
    source_width, source_height = source_size
    picture_height = min(region_height, region_width * source_height / source_width)
    return max(STUDIO_CAPTION_MARGIN, 1 - (center + picture_height / 2) / height - .11)


def probe(path: Path) -> tuple[float, int, int]:
    import cv2
    cap = cv2.VideoCapture(str(path))
    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not cap.isOpened() or not fps:
            raise ValueError(f"Cannot read video: {path}")
        return cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps, int(cap.get(3)), int(cap.get(4))
    finally:
        cap.release()


def face_track(path: Path, start: float, end: float) -> list[tuple[float, float]]:
    import cv2
    if not hasattr(cv2, 'CascadeClassifier') or not hasattr(cv2, 'data'):
        return []
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    if detector.empty():
        return []
    cap = cv2.VideoCapture(str(path))
    samples = []
    previous = None
    try:
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
        with Progress(SpinnerColumn(),TextColumn("Scanning faces"),BarColumn(),TaskProgressColumn(),TimeElapsedColumn()) as progress:
            samples_task=progress.add_task("Scanning faces",total=int(end-start)+1)
            for i in progress.track(range(int(end-start)+1),task_id=samples_task):
                cap.set(cv2.CAP_PROP_POS_MSEC, (start + i) * 1000)
                ok, frame = cap.read()
                if not ok:
                    continue
                small = cv2.resize(frame, (480, int(frame.shape[0] * 480 / frame.shape[1])))
                faces = detector.detectMultiScale(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), 1.1, 5)
                if len(faces):
                    x, _, w, _ = max(faces, key=lambda box: box[2] * box[3])
                    center = (x + w / 2) / 480
                    previous = center if previous is None else previous * .7 + center * .3
                    samples.append((float(i), previous))
    finally:
        cap.release()
    return samples


def cut(path: Path, clip, output: Path, aspect: str, framing: str = 'fit') -> None:
    import av
    _, sw, sh = probe(path)
    width, height = FORMATS[aspect]
    if framing not in FRAMING:
        raise ValueError('Unknown picture layout.')
    track = face_track(path, clip.start, clip.end) if framing == 'face' else []
    if framing == 'studio':
        region_width, region_height, center = studio_region(width, height)
        filters = (
            f"[0:v]scale={region_width}:{region_height}:force_original_aspect_ratio=decrease:"
            f"force_divisible_by=2,pad={width}:{height}:(ow-iw)/2:{center}-ih/2:"
            f"color=0x{STUDIO_BACKGROUND},setsar=1[v]"
        )
    elif framing == 'fit':
        filters = f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x10131c,setsar=1[v]"
    elif track:
        # Piecewise time-dependent horizontal crop, smoothed during face sampling.
        cw = min(sw, int(sh * width / height)) // 2 * 2
        ch = min(sh, int(sw * height / width)) // 2 * 2
        positions = [(t, max(0, min(sw - cw, center * sw - cw / 2))) for t, center in track]
        expr = str(round(positions[-1][1]))
        for t, x in reversed(positions[:-1]):
            expr = f"if(lt(t,{t+1}),{round(x)},{expr})"
        filters = f"[0:v]crop={cw}:{ch}:'{expr}':(ih-oh)/2,scale={width}:{height},setsar=1[v]"
    else:
        filters = f"[0:v]split[bg][fg];[bg]scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},boxblur=30:10[b];[fg]scale={width}:{height}:force_original_aspect_ratio=decrease[f];[b][f]overlay=(W-w)/2:(H-h)/2,setsar=1[v]"
    with av.open(str(path)) as container:
        has_audio=bool(container.streams.audio)
    inputs=[ffmpeg(), "-y", "-ss", str(clip.start), "-i", str(path)]
    if not has_audio:
        inputs += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    command(inputs + ["-t", str(clip.end-clip.start), "-filter_complex", filters, "-map", "[v]", "-map", "0:a:0" if has_audio else "1:a:0", "-c:v", "libx264", "-preset", "fast", "-crf", "22", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(output)],duration=clip.end-clip.start,title="Reframing clip")
