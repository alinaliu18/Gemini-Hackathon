"""Offline check that every run is saved: input at the start, output (or the error) at the end. The model is faked and the
data goes to a temp folder. Run: GEMINI_API_KEY=offline-placeholder ./.venv/bin/python tests/test_store.py"""
import io, json, os, sys, pathlib, sqlite3, subprocess, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["MAESTRO_DATA_DIR"] = tmp = tempfile.mkdtemp()
os.environ.setdefault("GEMINI_API_KEY", "offline-placeholder")
import backend

audio_bytes = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=300:duration=3", "-c:a", "libopus",
                              "-f", "webm", "-"], capture_output=True, check=True).stdout
REPORT = {"summary": {"score": 81, "strengths": [], "improvements": [], "dimensions": {}}, "answers": [], "segments": []}
backend.session_report = lambda *a, **k: (k.get("emit") or (lambda e: None))({"type": "stage", "total": 0}) or dict(REPORT)
client = backend.app.test_client()
turns = [{"role": "interviewer", "text": "Tell me about X.", "start": 0.5, "end": 2.5}]

def post(path, **extra):
    data = {"goal": "career", "turns": json.dumps(turns), "context_text": "Product intern role", "audio_response": (io.BytesIO(audio_bytes), "s.webm"), **extra}
    return client.post(path, data=data, content_type="multipart/form-data")

def rows():
    db = sqlite3.connect(pathlib.Path(tmp) / "maestro.db"); db.row_factory = sqlite3.Row
    return db.execute("SELECT * FROM runs ORDER BY rowid").fetchall()

# 1) streaming route, success
r = post("/api/session_report/stream", video_signals=json.dumps({"face_present_ratio": 0.9}))
events = [json.loads(l) for l in r.get_data(as_text=True).splitlines()]
assert events[-1]["type"] == "done", events
run = rows()[0]
assert run["status"] == "ok" and run["kind"] == "live" and run["score"] == 81, dict(run)
assert run["context_text"] == "Product intern role" and json.loads(run["turns_json"]) == turns
assert json.loads(run["video_json"]) == {"face_present_ratio": 0.9}
assert (pathlib.Path(tmp) / run["audio_path"]).stat().st_size > 1000, "recording not saved"
assert json.loads(run["report_json"])["summary"]["score"] == 81 and json.loads(run["report_json"])["run_id"] == run["id"]

# 2) plain route, model failure: the input is still there, with the error
def boom(*a, **k): raise RuntimeError("429 quota exceeded")
backend.session_report = boom
assert post("/api/session_report").status_code == 500
failed = rows()[-1]
assert failed["status"] == "error" and "429" in failed["error"] and failed["turns_json"] and failed["audio_path"], dict(failed)

# 3) STORE_AUDIO=0 keeps text only
os.environ["STORE_AUDIO"] = "0"
backend.session_report = lambda *a, **k: dict(REPORT)
post("/api/session_report")
assert rows()[-1]["audio_path"] is None and rows()[-1]["status"] == "ok"
os.environ.pop("STORE_AUDIO")

# 4) Quick Practice, typed answer
backend.with_client = lambda fn: (({"score": 70, "dimensions": {}, "strengths": [], "improvements": [], "dropped": [],
                                    "score_coverage": 1, "not_measured": []}), "m")
r = client.post("/api/evaluate", data={"goal": "career", "question": "Why this role?", "text_input": "Because I like users."},
                content_type="multipart/form-data")
assert r.status_code == 200, r.get_data(as_text=True)
p = rows()[-1]
assert p["kind"] == "practice" and p["question"] == "Why this role?" and p["typed_text"] == "Because I like users." and p["status"] == "ok" and p["score"] == 70, dict(p)
print("runs saved:", len(rows()), "| ALL OK")
