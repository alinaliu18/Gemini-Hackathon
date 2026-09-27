"""Offline check of how a live interview is split into answers. Run: ./.venv/bin/python tests/test_session.py"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pipeline.session import questions_from_turns, candidate_segments, answer_windows, answer_audio

turns = [
    {"role": "interviewer", "start": 1.0, "end": 6.0, "text": "Hi. Tell me about the sign-up redesign."},  # no "?" but a question
    {"role": "interviewer", "start": 12.0, "end": 13.0, "text": "What did you do?", "interrupted": True},  # cut off: not a question
    {"role": "interviewer", "start": 30.0, "end": 34.0, "text": "What was YOUR part?"},
    {"role": "interviewer", "start": 50.0, "end": 53.0, "text": "Thanks, your feedback report is being prepared."},  # sign-off
    {"role": "candidate_live", "t": 20.0, "text": "ignored"},
]
qs = questions_from_turns(turns)
assert [q["start"] for q in qs] == [1.0, 30.0]

segs = [{"start": 2.0, "end": 4.0, "text": "interviewer echo"},     # inside a playback window -> dropped
        {"start": 7.0, "end": 12.0, "text": "answer one a"},
        {"start": 16.0, "end": 28.0, "text": "answer one b"},
        {"start": 35.0, "end": 45.0, "text": "answer two"}]
cand = candidate_segments(segs, turns)
assert [s["text"] for s in cand] == ["answer one a", "answer one b", "answer two"]

wins = answer_windows(qs, 60.0)
assert [(round(a, 2), b) for _, a, b in wins] == [(5.7, 30.0), (33.7, 60.0)]  # question end -> next question start
ans = [{"segments": [s for s in cand if a <= s["start"] < b]} for _, a, b in wins]

audio_m = {"duration_s": 60, "speech_s": 30, "noisy": False, "long_pause_count": 2,
           "pauses": [{"start": 12.5, "duration": 3.5}, {"start": 46.0, "duration": 4.0}]}  # 2nd is after the answer ended
a1 = answer_audio(audio_m, ans[0]["segments"])
assert a1["duration_s"] == 21.0 and a1["speech_s"] == 17.0 and a1["long_pause_count"] == 1
assert answer_audio(audio_m, ans[1]["segments"])["pauses"] == []
print("ALL OK")
