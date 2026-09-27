"""Whole-interview report: split one recording into answers by the interviewer's questions, give feedback per answer,
and one overall summary for the session. Reuses the single-answer pipeline, so the same evidence rules apply."""
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor

from . import config
from .interpret import interpret, overall_score
from .transcribe import transcribe

VIDEO_DIMS = ("eye_contact", "presence")  # measured over the whole session, so shown only in the summary


CLOSING = re.compile(r"report is being prepared", re.I)  # the interviewer's sign-off (see live.py)


def questions_from_turns(turns):
    """Interviewer turns that were not cut off, minus the sign-off. "Tell me about..." is a question too, so no "?" check.
    A cut-off turn means the candidate kept answering the previous question. Times are seconds from recording start."""
    return [t for t in turns if t.get("role") == "interviewer" and (t.get("text") or "").strip()
            and not t.get("interrupted") and t.get("start") is not None and not CLOSING.search(t["text"])]


def candidate_segments(segments, turns):
    """Drop transcript segments that are the interviewer's voice leaking into the mic (midpoint inside a playback window)."""
    windows = [(t["start"], t["end"]) for t in turns if t.get("role") == "interviewer" and t.get("start") is not None]
    return [s for s in segments if not any(a <= (s["start"] + s["end"]) / 2 <= b for a, b in windows)]


def answer_windows(questions, duration):
    """Answer i runs from the end of question i to the start of question i+1 (or the end of the recording)."""
    return [(q, max(0.0, q["end"] - 0.3), questions[i + 1]["start"] if i + 1 < len(questions) else duration)
            for i, q in enumerate(questions)]


def transcribe_window(call, audio_path, start, end, out_path):
    """Transcribe one answer on its own and shift timestamps back onto the session clock. Short clips keep Gemini's
    timestamps accurate (on a long recording that opens with silence they drift) and keep the interviewer's voice out."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.2f}", "-to", f"{end:.2f}", "-i", audio_path,
                    "-ac", "1", "-ar", "16000", out_path], check=True)
    segs, _ = call(lambda c, m: transcribe(c, m, out_path, "audio/wav"))
    return [{**s, "start": round(s["start"] + start, 2), "end": round(s["end"] + start, 2)} for s in segs]


def answer_audio(audio_m, segs):
    """Audio facts restricted to one answer: only pauses inside it count (silence while the interviewer talks is not a pause)."""
    a, b = segs[0]["start"], segs[-1]["end"]
    pauses = [p for p in audio_m["pauses"] if a <= p["start"] and p["start"] + p["duration"] <= b]
    return {**audio_m, "duration_s": round(b - a, 2), "speech_s": round(sum(s["end"] - s["start"] for s in segs), 2),
            "pauses": pauses, "long_pause_count": sum(p["duration"] >= config.LONG_PAUSE_S for p in pauses)}


def session_report(call, goal, context, resume, audio_path, turns, audio_m, video, analyze_text):
    """`call(fn)` runs fn(client, model) with key/model fallback and returns (result, model).
    Returns {"summary", "answers", "segments"}; every timestamp is relative to the start of the recording."""
    windows = [w for w in answer_windows(questions_from_turns(turns), audio_m["duration_s"]) if w[2] - w[1] >= 1.0]
    with tempfile.TemporaryDirectory() as tmp, ThreadPoolExecutor(max_workers=max(1, len(windows))) as pool:
        seglists = list(pool.map(lambda iw: transcribe_window(call, audio_path, iw[1][1], iw[1][2], f"{tmp}/a{iw[0]}.wav"),
                                 enumerate(windows)))
    answers = []
    for (q, _, end), segs in zip(windows, seglists):
        segs = candidate_segments([s for s in segs if s["start"] < end], turns)  # drops a cut-off interviewer's voice
        if segs:
            answers.append({"question": q["text"], "asked_at": q["start"], "segments": segs})
    segments = [s for a in answers for s in a["segments"]]
    if not answers:
        return {"summary": None, "answers": [], "segments": [], "note": "No answers found in the recording."}

    def per_answer(a):
        text_m = analyze_text(a["segments"])  # pace from transcript timestamps: the answer windows are short
        res, _ = call(lambda c, m: interpret(c, m, a["question"], goal, resume, a["segments"],
                                             answer_audio(audio_m, a["segments"]), text_m, None))
        for k in VIDEO_DIMS:
            res["dimensions"].pop(k, None)
        res["score"] = overall_score(res["dimensions"], goal)
        res.pop("score_coverage", None); res.pop("not_measured", None)
        return {"question": a["question"], "asked_at": a["asked_at"], **res}

    def summary():
        segs = [s for a in answers for s in a["segments"]]
        speech = round(sum(s["end"] - s["start"] for s in segs), 2)
        pauses = [p for a in answers for p in answer_audio(audio_m, a["segments"])["pauses"]]
        audio_s = {**audio_m, "speech_s": speech, "pauses": pauses,
                   "long_pause_count": sum(p["duration"] >= config.LONG_PAUSE_S for p in pauses)}
        text_m = analyze_text(segs, speech)
        asked = " | ".join(a["question"] for a in answers)
        res, _ = call(lambda c, m: interpret(c, m, f"Whole interview. Questions asked: {asked}. {context}", goal,
                                             resume, segs, audio_s, text_m, video))
        res["strengths"], res["improvements"] = res["strengths"][:2], res["improvements"][:2]
        return res

    # ponytail: one thread per answer; fine for a 3-4 question interview, cap workers if sessions get long
    with ThreadPoolExecutor(max_workers=len(answers) + 1) as pool:
        s = pool.submit(summary)
        per = list(pool.map(per_answer, answers))
    return {"summary": s.result(), "answers": per, "segments": segments}
