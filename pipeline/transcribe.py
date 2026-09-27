"""Verbatim transcription with timestamps, so every piece of feedback can point back to what was said."""
import json

PROMPT = """Transcribe this interview answer VERBATIM.
- Keep every filler word exactly as spoken (um, uh, like, you know, 嗯, 呃). Do not clean up grammar.
- Split into segments at sentence boundaries, each at most ~10 seconds.
- Timestamps are seconds from the start of the audio (floats).
Return ONLY a JSON array: [{"start": 0.0, "end": 4.2, "text": "..."}]. If there is no speech, return []."""


def transcribe(client, model, audio_path, mime_type):
    """Upload audio to Gemini and return sorted, sanity-checked [{start, end, text}] segments."""
    uploaded = client.files.upload(file=audio_path, config={"mime_type": mime_type})
    resp = client.models.generate_content(
        model=model,
        contents=[PROMPT, uploaded],
        config={"response_mime_type": "application/json", "temperature": 0},
    )
    raw = json.loads(resp.text.replace("```json", "").replace("```", "").strip())
    segs = []
    for s in raw if isinstance(raw, list) else []:
        try:
            start, end, text = float(s["start"]), float(s["end"]), str(s["text"]).strip()
        except (KeyError, TypeError, ValueError):
            continue
        if text and end >= start >= 0:
            segs.append({"start": round(start, 2), "end": round(end, 2), "text": text})
    return sorted(segs, key=lambda s: s["start"])
