"""Whole-interview report: split one recording into answers by the interviewer's questions, give feedback per answer,
and one overall summary for the session. Reuses the single-answer pipeline, so the same evidence rules apply."""
import re
import subprocess
import tempfile
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock

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


def session_report(call, goal, context, resume, audio_path, turns, audio_m, video, analyze_text, emit=None):
    """`call(fn)` runs fn(client, model) with key/model fallback and returns (result, model).
    Returns {"summary", "answers", "segments"}; every timestamp is relative to the start of the recording.

    Each answer is transcribed and then interpreted on its own thread, so feedback for a short answer does not wait for
    the slowest transcription. The overall summary waits only for the transcripts. `emit(event)` is told about progress:
    {"type": "stage", "total"}, {"type": "transcribed", "done", "total"}, {"type": "answer", "index", "answer"},
    {"type": "summary", "summary"}. Without `emit` the function just returns the finished report."""
    emit = emit or (lambda event: None)
    windows = [w for w in answer_windows(questions_from_turns(turns), audio_m["duration_s"]) if w[2] - w[1] >= 1.0]
    emit({"type": "stage", "stage": "transcribing", "total": len(windows)})
    transcripts = [Future() for _ in windows]  # the summary needs all of them; each answer needs only its own
    done = {"n": 0}
    lock = Lock()

    def per_answer(a):
        text_m = analyze_text(a["segments"])  # pace from transcript timestamps: the answer windows are short
        res, _ = call(lambda c, m: interpret(c, m, a["question"], goal, resume, a["segments"],
                                             answer_audio(audio_m, a["segments"]), text_m, None))
        for k in VIDEO_DIMS:
            res["dimensions"].pop(k, None)
        res["score"] = overall_score(res["dimensions"], goal)
        res.pop("score_coverage", None); res.pop("not_measured", None)
        return {"question": a["question"], "asked_at": a["asked_at"], **res}

    def answer_task(i, window, tmp):
        q, start, end = window
        try:
            segs = transcribe_window(call, audio_path, start, end, f"{tmp}/a{i}.wav")
            segs = candidate_segments([s for s in segs if s["start"] < end], turns)  # drops a cut-off interviewer's voice
            a = {"question": q["text"], "asked_at": q["start"], "segments": segs} if segs else None
        except Exception as e:
            transcripts[i].set_exception(e)
            raise
        transcripts[i].set_result(a)
        with lock:
            done["n"] += 1
            emit({"type": "transcribed", "done": done["n"], "total": len(windows)})
        if a is None:
            return None
        res = per_answer(a)
        emit({"type": "answer", "index": i, "answer": res})
        return a, res

    def summary():
        answers = [a for a in (t.result() for t in transcripts) if a]
        if not answers:
            return None
        segs = [s for a in answers for s in a["segments"]]
        speech = round(sum(s["end"] - s["start"] for s in segs), 2)
        pauses = [p for a in answers for p in answer_audio(audio_m, a["segments"])["pauses"]]
        audio_s = {**audio_m, "speech_s": speech, "pauses": pauses,
                   "long_pause_count": sum(p["duration"] >= config.LONG_PAUSE_S for p in pauses)}
        text_m = analyze_text(segs, speech)
        asked = " | ".join(a["question"] for a in answers)
        res, _ = call(lambda c, m: interpret(c, m, f"Whole interview. Questions asked: {asked}. {context}", goal,
                                             resume, segs, audio_s, text_m, video))
        res["strengths"], res["improvements"] = res["strengths"][:2], res["improvements"][:3]
        emit({"type": "summary", "summary": res})
        return res

    # ponytail: one thread per answer; fine for a 3-4 question interview, cap workers if sessions get long
    with tempfile.TemporaryDirectory() as tmp, ThreadPoolExecutor(max_workers=len(windows) + 1) as pool:
        tasks = [pool.submit(answer_task, i, w, tmp) for i, w in enumerate(windows)]
        s = pool.submit(summary)
        results = [t.result() for t in tasks]
        summ = s.result()
    results = [r for r in results if r]
    if not results:
        return {"summary": None, "answers": [], "segments": [], "note": "No answers found in the recording."}
    answers = [r[1] for r in results]
    summ["improvements"] = top_up(summ["improvements"], answers, 3)
    return {"summary": summ, "answers": answers, "segments": [seg for a, _ in results for seg in a["segments"]]}


def top_up(improvements, answers, n):
    """The report leads with the `n` most useful fixes. The summary alone sometimes finds fewer, so fill the rest from
    the per-answer feedback (skipping repeats), keeping only items that carry evidence."""
    out = list(improvements)
    seen = {i["text"].strip().lower() for i in out}
    for a in answers:
        for item in a.get("improvements", []):
            key = item["text"].strip().lower()
            if len(out) >= n:
                return out
            if key not in seen and item.get("evidence"):
                out.append(item); seen.add(key)
    return out
