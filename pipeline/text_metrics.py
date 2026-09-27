"""Text metrics from transcript segments: words, WPM, and filler words."""
import re

WORD_RE = re.compile(r"[A-Za-z']+|[一-鿿]")
CN_FILLERS = ["嗯", "呃"]
# "like" only counts when immediately followed by a comma
FILLER_RE = re.compile(
    r"(?<![\w'])(um|uh|erm|er|hmm|you know|i mean|like(?=,))(?![\w'])", re.IGNORECASE)


def analyze_text(segments, speech_s=None):
    """Return word count, WPM, and filler-word stats for transcript segments."""
    full = " ".join(seg["text"] for seg in segments)
    word_count = len(WORD_RE.findall(full))
    if speech_s:
        minutes = speech_s / 60
    elif segments:
        minutes = (segments[-1]["end"] - segments[0]["start"]) / 60
    else:
        minutes = 0
    wpm = word_count / minutes if minutes else 0

    breakdown = {}
    events = []
    for seg in segments:
        text = seg["text"]
        for m in FILLER_RE.finditer(text):
            term = m.group(1).lower()
            breakdown[term] = breakdown.get(term, 0) + 1
            events.append({"t": seg["start"], "term": term})
        for ch in CN_FILLERS:
            n = text.count(ch)
            if n:
                breakdown[ch] = breakdown.get(ch, 0) + n
                events.extend({"t": seg["start"], "term": ch} for _ in range(n))
    breakdown = {k: v for k, v in breakdown.items() if v > 0}
    filler_count = sum(breakdown.values())
    return {
        "word_count": word_count,
        "wpm": round(wpm, 2),
        "segment_wpm": [
            {"start": seg["start"], "end": seg["end"],
             "wpm": round(len(WORD_RE.findall(seg["text"])) /
                          ((seg["end"] - seg["start"]) / 60), 2)
             if seg["end"] > seg["start"] else 0}
            for seg in segments
        ],
        "filler_count": filler_count,
        "fillers_per_min": round(filler_count / minutes, 2) if minutes else 0,
        "filler_breakdown": breakdown,
        "filler_events": events,
    }
