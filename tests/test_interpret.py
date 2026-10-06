"""Offline check that the hard rules are enforced in code, not left to the model. Run: ./.venv/bin/python tests/test_interpret.py"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pipeline.interpret import validate, overall_score, score_fillers

segments = [{"start": 0, "end": 5, "text": "Um so I led a team of four to rebuild the onboarding flow."},
            {"start": 5, "end": 12, "text": "We cut drop-off from forty to twenty percent in two weeks."}]
fake_model = {
    "dimensions": {
        "content": {"score": 80, "observation": "Clear result with a number.",
                    "evidence": [{"t": "0:05", "quote": "cut drop-off from forty to twenty percent"}]},
        "structure": {"score": 70, "observation": "Action and result, little situation.",
                      "evidence": [{"t": "0:00", "quote": "this sentence was never said"}]},       # fabricated quote -> dropped
        "clarity": {"score": 90, "observation": "Articulate.", "evidence": [{"t": "0:00", "quote": "I led a team of four"}]},
        "presence": {"score": 60, "observation": "You looked nervous at the start.",                # emotion -> dropped
                     "evidence": [{"t": "0:01", "signal": "smile"}]},
    },
    "strengths": [{"text": "Concrete metric.", "evidence": [{"t": "0:05", "quote": "forty to twenty percent"}]},
                  {"text": "Great energy.", "evidence": []}],                                        # no evidence -> dropped
    "improvements": [{"text": "Smiling showed you were not confident.", "tip": "Stop smiling.",        # emotion -> dropped
                      "evidence": [{"t": "0:01", "signal": "smile"}]},
                     {"text": "Add the situation first.", "tip": "Open with one sentence of context.",
                      "evidence": [{"t": "0:00", "quote": "Um so I led a team"}]}],
}

# noisy recording + video present
clean, dropped = validate(fake_model, segments, clarity_scorable=False, has_video=True)
d = clean["dimensions"]
assert d["content"]["score"] == 80
assert d["structure"]["score"] is None, "fabricated quote must not count as evidence"
assert d["clarity"]["score"] is None and "noisy" in d["clarity"]["observation"]
assert d["presence"]["score"] is None, "emotion inference must be removed"
assert [s["text"] for s in clean["strengths"]] == ["Concrete metric."]
assert [i["text"] for i in clean["improvements"]] == ["Add the situation first."]
assert {x["why"] for x in dropped} == {"no verifiable evidence", "emotion inference"}

# no video -> presence forced null even if model scored it
clean2, _ = validate({"dimensions": {"presence": {"score": 90, "observation": "Steady.", "evidence": [{"t": "0:01", "signal": "motion 0.1"}]}}},
                     segments, clarity_scorable=True, has_video=False)
assert clean2["dimensions"]["presence"]["score"] is None

# overall score skips null dimensions and uses track weights
dims = {"content": {"score": 80}, "structure": {"score": None}, "pacing": {"score": 90}, "eye_contact": {"score": None}}
assert overall_score(dims, "Career") == round((.30 * 80 + .10 * 90) / .40)

from pipeline.interpret import score_coverage
cov, missing = score_coverage({"content": {"score": 80}, "pacing": {"score": 90}, "clarity": {"score": None},
                               "structure": {"score": 70}, "filler_words": {"score": 75}, "eye_contact": {"score": None}, "presence": {"score": None}}, "Career")
assert cov == 0.65 and missing == ["clarity", "eye_contact", "presence"]

# filler scoring bands
tm = {"fillers_per_min": 5.0, "filler_count": 5, "filler_breakdown": {"um": 3, "like": 2}, "filler_events": [{"t": 1, "term": "um"}]}
assert score_fillers(tm)["score"] == 60

from pipeline.interpret import score_eye_contact
assert score_eye_contact({"face_present_ratio": 0.2, "eye_contact_ratio": 0.0, "look_away_events": []})["score"] is None

print("ALL OK")
