"""Verbatim transcription with timestamps, so every piece of feedback can point back to what was said."""
import json
from pathlib import Path

from google.genai import types

INLINE_LIMIT = 15 * 1024 * 1024  # Gemini takes up to 20 MB of inline data per request; above that, use the Files API

PROMPT = """Transcribe this interview answer VERBATIM.
- Keep every filler word exactly as spoken (um, uh, like, you know, 嗯, 呃). Do not clean up grammar.
- Split into segments at sentence boundaries, each at most ~10 seconds.
- Timestamps are strings in MM:SS format from the start of the audio (e.g. "01:07" is 67 seconds in).
Return ONLY a JSON array: [{"start": "00:00", "end": "00:04", "text": "..."}]. If there is no speech, return []."""


def to_seconds(ts):
    """ "MM:SS", "H:MM:SS" or "MM:SS.s" -> seconds. Plain numbers are taken as seconds.
    (Asked for as MM:SS because Gemini, left to write floats, sometimes writes 0.45 meaning 0:45.)"""
    if isinstance(ts, (int, float)):
        return float(ts)
    secs = 0.0
    for part in str(ts).strip().split(":"):
        secs = secs * 60 + float(part)
    return secs


def transcribe(client, model, audio_path, mime_type):
    """Send audio to Gemini and return sorted, sanity-checked [{start, end, text}] segments."""
    data = Path(audio_path).read_bytes()
    audio = types.Part.from_bytes(data=data, mime_type=mime_type) if len(data) < INLINE_LIMIT \
        else client.files.upload(file=audio_path, config={"mime_type": mime_type})  # inline skips an upload round trip
    resp = client.models.generate_content(
        model=model,
        contents=[PROMPT, audio],
        config={"response_mime_type": "application/json", "temperature": 0},
    )
    raw = json.loads(resp.text.replace("```json", "").replace("```", "").strip())
    segs = []
    for s in raw if isinstance(raw, list) else []:
        try:
            start, end, text = to_seconds(s["start"]), to_seconds(s["end"]), str(s["text"]).strip()
        except (KeyError, TypeError, ValueError):
            continue
        if text and end >= start >= 0:
            segs.append({"start": round(start, 2), "end": round(end, 2), "text": text})
    return sorted(segs, key=lambda s: s["start"])
