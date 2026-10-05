"""Offline check of the progressive report: event order, no barrier between transcription and feedback, and the
top-up to three fixes. Model calls are faked. Run: ./.venv/bin/python tests/test_session_stream.py"""
import sys, pathlib, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pipeline.session as S

turns = [{"role": "interviewer", "start": 1.0, "end": 4.0, "text": "Tell me about project A."},
         {"role": "interviewer", "start": 20.0, "end": 23.0, "text": "What was your part?"},
         {"role": "interviewer", "start": 40.0, "end": 43.0, "text": "What would you change?"}]
audio_m = {"duration_s": 60, "speech_s": 40, "noisy": False, "long_pause_count": 0, "pauses": []}
DELAY = {0: 0.05, 1: 0.30, 2: 0.05}  # answer 1 transcribes slowest

def fake_transcribe(call, path, start, end, out):
    i = round((start - 3.7) / 20)
    time.sleep(DELAY[i])
    return [{"start": start + 1, "end": start + 5, "text": f"answer {i} words here"}]

def fake_interpret(client, model, question, goal, resume, segs, audio, text_m, video):
    n = 2 if "Whole interview" in question else 1
    return {"dimensions": {"content": {"score": 80, "observation": "ok", "evidence": []}}, "strengths": [], "score": 80,
            "improvements": [{"text": f"fix {question[:12]} #{k}", "tip": "t", "evidence": [{"t": "0:05", "quote": "q"}]} for k in range(n)],
            "score_coverage": 1, "not_measured": [], "dropped": []}

S.transcribe_window, S.interpret = fake_transcribe, fake_interpret
events = []
rep = S.session_report(lambda fn: (fn(None, None), None), "Career", "", "resume", "x.wav", turns, audio_m, None,
                       lambda segs, speech=None: {"wpm": 150}, emit=events.append)

kinds = [e["type"] for e in events]
assert kinds[0] == "stage" and events[0]["total"] == 3, kinds
assert kinds.count("transcribed") == 3 and kinds.count("answer") == 3 and kinds.count("summary") == 1, kinds
# No barrier: answer 0 is ready before the slow transcription of answer 1 has finished.
first_answer = kinds.index("answer")
last_transcribed = max(i for i, k in enumerate(kinds) if k == "transcribed")
assert first_answer < last_transcribed, kinds
# The summary waits for every transcript.
assert kinds.index("summary") > last_transcribed, kinds
assert [a["asked_at"] for a in rep["answers"]] == [1.0, 20.0, 40.0]  # final answers stay in question order
assert len(rep["summary"]["improvements"]) == 3, rep["summary"]["improvements"]  # 2 from the summary + 1 topped up
assert S.top_up([], [{"improvements": [{"text": "A", "evidence": []}, {"text": "B", "evidence": [{"t": "0:01", "quote": "x"}]}]}], 3) \
    == [{"text": "B", "evidence": [{"t": "0:01", "quote": "x"}]}]  # items without evidence never fill the list
print("ALL OK")
