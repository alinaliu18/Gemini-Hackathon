"""Offline checks of the live interviewer's follow-up decisions and the suggested next practice. The model is faked.
Run: GEMINI_API_KEY=offline-placeholder ./.venv/bin/python tests/test_agent.py"""
import json, os, pathlib, sqlite3, sys, tempfile, time
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["MAESTRO_DATA_DIR"] = tmp = tempfile.mkdtemp()
os.environ.setdefault("GEMINI_API_KEY", "offline-placeholder")
os.environ.setdefault("MAESTRO_SECRET", "test-secret")
from pipeline import followup, nextplan, config, store
from pipeline.live import system_instruction, live_config

def decided(missing, ask=""):
    return lambda call, q, a, n: (missing, ask)

# 1) missing items are asked about in a fixed order, a bare "missing" gets a written question
d = followup.decide(None, "Q", "We shipped it.", 0, decider=decided(["result_number", "own_action"], ""))
assert d["action"] == "follow_up" and d["missing"] == "own_action" and d["ask"] == followup.ASK["own_action"], d
d = followup.decide(None, "Q", "I cut costs 20%.", 0, decider=decided([], ""))
assert d["action"] == "next" and d["source"] == "model", d
# 2) at most two follow-ups per main question, and the model is not even asked the third time
called = []
d = followup.decide(None, "Q", "x", 2, decider=lambda *a: called.append(1) or (["example"], ""))
assert d["action"] == "next" and d["source"] == "cap" and not called, d
# 3) too slow: the old rule, one follow-up per question, and it says so
slow = lambda *a: time.sleep(0.5) or (["example"], "")
d0 = followup.decide(None, "Q", "x", 0, timeout=0.05, decider=slow)
d1 = followup.decide(None, "Q", "x", 1, timeout=0.05, decider=slow)
assert (d0["action"], d0["source"]) == ("follow_up", "timeout_fallback") and d1["action"] == "next", (d0, d1)
assert d0["ms"] < 400, d0
d = followup.decide(None, "Q", "x", 0, decider=lambda *a: 1 / 0)
assert d["source"] == "error_fallback" and d["action"] == "follow_up", d
# 4) model output is checked, junk means "move on"
assert followup.parse('{"missing": ["example", "vibes"], "ask": " Which time? "}') == (["example"], "Which time?")
assert followup.parse("not json") == ([], "") and followup.parse('{"missing": "example"}') == ([], "")
# 5) every decision is recorded, without the answer text
db = sqlite3.connect(pathlib.Path(tmp) / "maestro.db")
rows = db.execute("SELECT action, missing, source, answer_words FROM followup_decisions").fetchall()
assert len(rows) == 6 and ("follow_up", "", "timeout_fallback", 1) in rows, rows
assert "We shipped" not in json.dumps(rows)

# 6) the interviewer is given the tool and told to wait for it
inst = system_instruction("Career", "resume", "job", plan_line=nextplan.first_question_line(
    {"label": "Structure", "how": "telling it in order"}))
assert "decide_next_step BEFORE you say anything" in inst and "Your FIRST main question" in inst
assert live_config(inst)["tools"][0]["function_declarations"][0]["name"] == "decide_next_step"
assert "exactly one follow-up" not in inst, "the old fixed rule is gone from the instructions"

# 7) weakest part: only scored dimensions count, live reports fall back to per-answer scores
rep = {"summary": {"dimensions": {"content": {"score": 80}, "structure": {"score": 55}, "eye_contact": {"score": None}}}}
assert nextplan.suggestion(rep)["dimension"] == "structure"
assert nextplan.suggestion({"answers": [{"dimensions": {"pacing": {"score": 40}, "content": {"score": 90}}},
                                        {"dimensions": {"pacing": {"score": 60}}}]})["dimension"] == "pacing"
assert nextplan.suggestion({"summary": {"dimensions": {}}}) is None

# 8) the routes: decision, plan only on agreement, link opens a plan, someone else's report is refused
import backend
backend.followup.model_decision = decided(["own_action"], "You said 'we shipped'. What did you do?")
c = backend.app.test_client()
H = {"X-Visitor-Id": "11111111-2222-3333-4444-555555555555"}
r = c.post("/api/followup", json={"main_question": "Tell me about X", "answer": "We shipped it.", "followups_asked": 0}, headers=H)
assert r.status_code == 200 and r.get_json()["missing"] == "own_action", r.get_json()

run_id = store.start_run("practice", "Career", "jd", "resume", visitor_id=H["X-Visitor-Id"])
store.finish_run(run_id, report={"score": 60, "dimensions": {"clarity": {"score": 45}, "content": {"score": 70}}})
assert not db.execute("SELECT COUNT(*) FROM plans").fetchone()[0], "a plan must not exist before the person agrees"
r = c.post("/api/next_session", json={"run_id": run_id, "starts_at": "2026-11-10T19:00:00-08:00"}, headers=H)
out = r.get_json()
assert r.status_code == 200 and out["label"] == "Clarity", out
assert "DTSTART:20261111T030000Z" in out["ics"] and out["link"] in out["ics"].replace("\r\n", "") and "?plan=" in out["link"], out["ics"]
assert db.execute("SELECT COUNT(*) FROM events WHERE name='next_session_agreed'").fetchone()[0] == 1
p = c.get(f"/api/plan/{out['plan_id']}").get_json()
assert p["dimension"] == "clarity", p
assert c.get("/api/plan/nope").status_code == 404
r = c.post("/api/next_session", json={"run_id": run_id}, headers={"X-Visitor-Id": "99999999-2222-3333-4444-555555555555"})
assert r.status_code == 403, r.get_json()
r = c.post("/api/next_session", json={"run_id": run_id, "starts_at": "2026-11-10T19:00"}, headers=H)
assert r.status_code == 400, "a time without a zone is refused"

# 9) a planned practice tells the interviewer to start on that part
seen = {}
backend.mint_token = lambda client, model, instruction: seen.setdefault("i", instruction) and "tok"
backend.TOKEN_CLIENTS = ["k"]
pdf = (ROOT / "tests/fixtures/resume.pdf").read_bytes()
import io
jd = " ".join(["Run user research, write specs and work with engineers on the product."] * 3)
r = c.post("/api/live/token", data={"goal": "career", "context_text": jd, "plan_id": out["plan_id"],
                                     "file": (io.BytesIO(pdf), "r.pdf")}, headers={"X-Visitor-Id": "77777777-2222-3333-4444-555555555555"},
           content_type="multipart/form-data")  # a visitor who has not used the free practice yet
assert r.status_code == 200, r.get_json()
assert "today starts with clarity" in seen["i"], seen["i"][-400:]
print("ALL OK")
