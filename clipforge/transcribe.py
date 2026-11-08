"""Cached CPU transcription with word timestamps."""
import hashlib
import json
import os
from pathlib import Path
from .config import home


def fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def transcribe(path: Path, model: str = "base", source_language: str = 'auto', caption_language: str = 'en', vad_filter: bool = True) -> list[dict]:
    """Produce English translations by default; keep language-specific caches separate."""
    if caption_language not in ('en','original'):
        raise ValueError('Caption language must be en or original.')
    if source_language != 'auto' and not (source_language.isalpha() and len(source_language) in (2,3)):
        raise ValueError('Use a source language code such as en, ar or auto.')
    if caption_language == 'en' and source_language != 'en' and model.endswith('.en'):
        raise ValueError('Use a multilingual Whisper model (base, small or medium) to translate non-English audio.')
    task = 'translate' if caption_language == 'en' and source_language != 'en' else 'transcribe'
    cache_key=hashlib.sha256(json.dumps([fingerprint(path),model,source_language,caption_language,vad_filter]).encode()).hexdigest()[:32]
    cached = home() / "cache" / f"transcript-v3-{cache_key}.json"
    cached.parent.mkdir(parents=True, exist_ok=True)
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    import av
    with av.open(str(path)) as container:
        if not container.streams.audio:
            cached.write_text("[]",encoding="utf-8")
            return []
    # Public Whisper models need no account. Windows can cache by copying files.
    os.environ.setdefault('HF_HUB_DISABLE_SYMLINKS_WARNING', '1')
    from faster_whisper import WhisperModel
    segments, _ = WhisperModel(model, device="cpu", compute_type="int8").transcribe(str(path), language=None if source_language=='auto' else source_language, task=task, word_timestamps=True, vad_filter=vad_filter, condition_on_previous_text=False)
    words = [{"start": w.start, "end": w.end, "word": w.word.strip()} for s in segments for w in (s.words or [])]
    cached.write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    return words
