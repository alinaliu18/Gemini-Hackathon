"""End-to-end smoke test against the real Gemini API (needs .env). Run: ./.venv/bin/python tests/e2e_smoke.py"""
import json, sys, pathlib, re
root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
import backend

VIDEO = {"duration_s": 22.0, "face_present_ratio": 0.98, "eye_contact_ratio": 0.72,
         "look_away_events": [{"start": 9.0, "end": 12.0, "duration": 3.0}],
         "smile_events": [{"start": 0.5, "end": 1.4, "peak": 0.8}], "motion_mean": 0.12, "motion_p90": 0.3}
EMO = re.compile(r"nervous|anxious|not confident|lack of confidence|紧张|不自信", re.I)

def run(fixture, video):
    c = backend.app.test_client()
    with open(root / "tests/fixtures" / fixture, "rb") as f:
        data = {"goal": "Career", "question": "Tell me about a product decision you made using user research.",
                "audio_response": (f, fixture, "audio/webm")}
        if video: data["video_signals"] = json.dumps(video)
        r = c.post("/api/evaluate", data=data, content_type="multipart/form-data")
    return r.status_code, r.get_json()

ok = True
for fixture, video in [("answer.webm", VIDEO), ("answer_noisy.webm", None)]:
    code, j = run(fixture, video)
    a = j["signals"]["audio"]; t = j["signals"]["text"]; d = j["dimensions"]
    print(f"\n=== {fixture}: HTTP {code}, score {j['score']}, total {j['timings'].get('total_ms')} ms")
    print(f"audio: {a['duration_s']}s, snr {a['snr_db']} dB, noisy={a['noisy']}, pauses={[(p['start'], p['duration']) for p in a['pauses']]}")
    print(f"text: {t['wpm']} wpm, fillers {t['filler_breakdown']}")
    for k, v in d.items():
        print(f"  {k:13s} {str(v['score']):>4s}  {v['observation'][:90]}  ev={len(v['evidence'])}")
    print("strengths:", [s['text'][:70] for s in j['strengths']])
    print("improvements:", [i['text'][:70] for i in j['improvements']])
    print("dropped by rules:", j['dropped'])
    checks = {
        "HTTP 200": code == 200,
        "no emotion words in output": not EMO.search(json.dumps({k: j[k] for k in ("dimensions", "strengths", "improvements", "congruence")})),
        "every item has evidence": all(x["evidence"] for x in j["strengths"] + j["improvements"]),
    }
    if fixture == "answer_noisy.webm":
        checks["noisy -> clarity null"] = a["noisy"] and d["clarity"]["score"] is None
        checks["noisy -> pauses not judged"] = "Pauses not measured" in d["pacing"]["observation"]
        checks["no video -> eye_contact null"] = d["eye_contact"]["score"] is None
    else:
        checks["clean -> clarity scored"] = (not a["noisy"]) and d["clarity"]["score"] is not None
        checks["3.5s pause found"] = any(abs(p["duration"] - 3.5) < 0.6 for p in a["pauses"])
        checks["fillers counted"] = t["filler_count"] >= 2
        checks["look-away cited"] = any("looked away" in e.get("signal", "") for e in d["eye_contact"]["evidence"])
    for k, v in checks.items():
        print(("  PASS " if v else "  FAIL ") + k); ok &= v
print("\nE2E", "ALL OK" if ok else "HAS FAILURES")
