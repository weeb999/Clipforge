"""Validate LLM selections before passing times to ffmpeg."""
import json
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Clip:
    start: float
    end: float
    hook: str
    score: float


def manual_clip(start: float, length: float, duration: float) -> Clip:
    """Validate an explicit trim without an LLM."""
    if not all(math.isfinite(value) for value in (start, length, duration)) or not (0 <= start and 20 <= length <= 60 and start + length <= duration):
        raise ValueError('Manual clip must be 20–60 seconds and fit within the source video.')
    return Clip(start, start + length, 'Manual clip', 0)


def evenly_spaced(duration: float, count: int, minimum: int, maximum: int) -> list[Clip]:
    """Distribute non-overlapping clips across the source without AI ranking."""
    if count < 1 or not 20 <= minimum <= maximum <= 60 or not math.isfinite(duration) or duration < count * minimum:
        raise ValueError('The source is too short for this many clips at the selected length. Reduce clip count or length.')
    length = min(maximum, duration / count)
    gap = max(0, (duration - length * count) / max(1, count - 1))
    result = []
    for index in range(count):
        start = min(index * (length + gap), duration - length)
        result.append(Clip(start, min(duration, start + length), f'Clip {index + 1}', 0))
    return result


def parse_clips(data: dict | str, duration: float, count: int, minimum: int = 20, maximum: int = 60) -> list[Clip]:
    if isinstance(data, str):
        data = json.loads(data)
    rows = data.get("clips")
    if not isinstance(rows, list) or not 1 <= len(rows) <= count:
        raise ValueError("LLM must return between one and the requested number of clips.")
    clips = []
    for row in rows:
        start, end, score = float(row["start"]), float(row["end"]), float(row["score"])
        hook = row["hook"]
        if not all(math.isfinite(n) for n in (start, end, score)) or not (0 <= start < end <= duration and minimum <= end - start <= maximum and 0 <= score <= 100):
            raise ValueError("Invalid clip bounds, length, or score.")
        if not isinstance(hook, str) or not hook.strip() or len(hook) > 200:
            raise ValueError("Clip hook must contain 1-200 characters.")
        if any(start < c.end and end > c.start for c in clips):
            raise ValueError("LLM selected overlapping clips.")
        clips.append(Clip(start, end, hook.strip(), score))
    return clips


def select(llm, words: list[dict], duration: float, count: int, minimum: int, maximum: int, images: list[str] | None = None) -> list[Clip]:
    prompt = f"Pick up to {count} non-overlapping engaging clips, each {minimum}-{maximum} seconds. Strong hook, complete thought, clean sentence start/end. Times must be within 0..{duration}. Return {{clips:[{{start:seconds,end:seconds,hook:title,score:0-100}}]}}. Transcript: " + json.dumps(words)
    if images:
        prompt += f"\nThe attached {len(images)} ordered frames are sampled at (i+0.5)*{duration}/{len(images)} seconds, i=0..{len(images)-1}. Use the visual sequence to select segments; do not invent speech."
    error = ""
    for _ in range(3):
        try:
            return parse_clips(llm.json(prompt + error, images), duration, count, minimum, maximum)
        except (ValueError, KeyError, TypeError) as exc:
            error = f"\nPrevious output failed validation: {exc}. Correct the JSON."
    raise ValueError("LLM returned invalid clip selections after three attempts." + error)
