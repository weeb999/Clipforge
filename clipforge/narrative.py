"""Frame-based non-speech briefing, with optional local TTS."""
import base64
from pathlib import Path
from .config import command, ffmpeg


def sample_frames(source: Path, start: float, end: float, count: int = 6) -> list[str]:
    import cv2
    cap = cv2.VideoCapture(str(source))
    images = []
    try:
        for i in range(count):
            cap.set(cv2.CAP_PROP_POS_MSEC, (start+(end-start)*(i+.5)/count)*1000)
            ok, frame = cap.read()
            if ok:
                frame = cv2.resize(frame, (640, round(frame.shape[0]*640/frame.shape[1])))
                ok, encoded = cv2.imencode(".jpg", frame)
                if ok:
                    images.append("data:image/jpeg;base64,"+base64.b64encode(encoded).decode())
    finally:
        cap.release()
    if not images:
        raise ValueError("Could not sample video frames.")
    return images


def narrate(llm, source: Path, start: float, end: float, caption_language: str = 'en') -> list[dict]:
    images=sample_frames(source,start,end)
    language = 'Write in English only, translating visible text if needed.' if caption_language == 'en' else 'Use the language visible in the source, or English if it is unclear.'
    data = llm.json("These ordered frames depict a short video. Write a factual, concise narrative, without invented details. " + language + " Return {\"narrative\":\"30-60 words describing the visible sequence\"}.", images)
    text = data.get("narrative", "")
    if not isinstance(text, str) or not 3 <= len(text.split()) <= 120:
        raise ValueError("Vision model returned an invalid narrative.")
    tokens = text.split()
    step = (end-start)/len(tokens)
    return [{"word":word, "start":start+i*step, "end":start+(i+1)*step} for i,word in enumerate(tokens)]


def voiceover(source: Path, words: list[dict], output: Path) -> None:
    try:
        import pyttsx3
    except ImportError as exc:
        raise RuntimeError('Install clipforge[tts] to enable local TTS.') from exc
    wav = output.with_suffix(".wav")
    engine = pyttsx3.init()
    engine.setProperty("rate", 165)
    engine.save_to_file(" ".join(w["word"] for w in words), str(wav))
    engine.runAndWait()
    command([ffmpeg(), "-y", "-i", str(source), "-i", str(wav), "-map", "0:v", "-map", "1:a", "-af", "apad", "-shortest", "-c:v", "copy", "-c:a", "aac", str(output)])
