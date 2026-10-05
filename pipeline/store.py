"""Every run is saved: the input when it starts, the output when it finishes (or the error if it fails), so nothing is lost
when the model call fails. One SQLite file plus the recordings, under data/ (gitignored: recordings of real people never go
in git). Set MAESTRO_DATA_DIR to move it, STORE_AUDIO=0 to keep text only. Show recent runs: python -m pipeline.store"""
import json
import os
import shutil
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(os.environ.get("MAESTRO_DATA_DIR") or Path(__file__).resolve().parents[1] / "data")

SCHEMA = """CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    finished_at TEXT,
    kind TEXT NOT NULL,            -- 'live' (whole interview) or 'practice' (one question)
    status TEXT NOT NULL,          -- 'running', 'ok' or 'error'
    goal TEXT,
    context_text TEXT,
    resume_text TEXT,
    question TEXT,
    typed_text TEXT,
    turns_json TEXT,               -- the interviewer's turns with times (live only)
    video_json TEXT,               -- on-device camera measurements, never video
    audio_path TEXT,               -- relative to the data dir
    audio_mime TEXT,
    report_json TEXT,              -- the full output
    score INTEGER,
    error TEXT,
    timings_json TEXT)"""


def _connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATA_DIR / "maestro.db", timeout=10)
    db.execute(SCHEMA)
    return db


def _dumps(x):
    return json.dumps(x, ensure_ascii=False) if x is not None else None


def start_run(kind, goal=None, context_text=None, resume_text=None, question=None, typed_text=None,
              turns=None, video=None, audio_src=None, audio_mime=None):
    """Save the input. Returns the run id. `audio_src` is copied, so the caller can delete its temp file."""
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
    audio_rel = None
    if audio_src and os.environ.get("STORE_AUDIO", "1") != "0":
        audio_rel = f"audio/{run_id}{Path(audio_src).suffix or '.webm'}"
        (DATA_DIR / "audio").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(audio_src, DATA_DIR / audio_rel)
    with _connect() as db:
        db.execute("INSERT INTO runs (id, created_at, kind, status, goal, context_text, resume_text, question, typed_text,"
                   " turns_json, video_json, audio_path, audio_mime) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (run_id, datetime.now().isoformat(timespec="seconds"), kind, "running", goal, context_text, resume_text,
                    question, typed_text, _dumps(turns), _dumps(video), audio_rel, audio_mime))
    return run_id


def finish_run(run_id, report=None, error=None, timings=None):
    """Save the output, or the error."""
    score = None
    if report:
        s = report.get("summary") if isinstance(report.get("summary"), dict) else report
        score = s.get("score") if isinstance(s, dict) else None
    with _connect() as db:
        db.execute("UPDATE runs SET finished_at=?, status=?, report_json=?, score=?, error=?, timings_json=? WHERE id=?",
                   (datetime.now().isoformat(timespec="seconds"), "error" if error else "ok", _dumps(report), score,
                    str(error) if error else None, _dumps(timings), run_id))


def recent(n=10):
    with _connect() as db:
        return db.execute("SELECT id, created_at, kind, status, goal, score, substr(coalesce(error,''),1,60), audio_path"
                          " FROM runs ORDER BY rowid DESC LIMIT ?", (n,)).fetchall()


if __name__ == "__main__":
    rows = recent(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
    print(f"{DATA_DIR / 'maestro.db'}: showing {len(rows)} most recent runs")
    for r in rows:
        print("  ", " | ".join("-" if v is None or v == "" else str(v) for v in r))
