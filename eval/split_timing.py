"""Split timing test for the report speed-up in 887a9bf, which shipped three changes at once: thinking off, no stage
barrier between transcribing and scoring, and streaming. README credited the whole 29.5 s to 9 to 15 s drop to thinking.

Each configuration changes one thing from the old setup. Streaming does not change how long the work takes, only when
the first piece reaches the page, so it needs no runs of its own: every run records both the total time and the time of
the first answer's feedback. Without streaming the page shows nothing until the total; with it, at the first answer.

  baseline   thinking on (model default), barrier on        how it was before 887a9bf
  thinking   thinking off, barrier on
  pipeline   thinking on, barrier off
  all        thinking off, barrier off                      how it is now

The session is synthetic and the same every time: three answers from tests/fixtures joined with gaps where the
interviewer speaks. One report is 7 model calls (3 transcriptions, 3 answers, 1 summary). The free tier allows about 20
per model per key per day, so pace it and spread runs over days:

  ./.venv/bin/python eval/split_timing.py --config baseline --reps 1
  ./.venv/bin/python eval/split_timing.py --config all --reps 2 --pause 90
  ./.venv/bin/python eval/split_timing.py --summary             # medians from eval/split_timing.csv
  ./.venv/bin/python eval/split_timing.py --mock --config all   # checks the harness with fake latencies, no model calls

Every run is appended to eval/split_timing.csv (mock runs to eval/split_timing_mock.csv) with the model that answered,
because a run where the fallback model answered is not comparable with the others.
"""
import argparse, csv, os, random, statistics, subprocess, sys, tempfile, time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FIX = ROOT / "tests" / "fixtures"
CONFIGS = {"baseline": (None, False), "thinking": (0, False), "pipeline": (None, True), "all": (0, True)}  # (budget, pipelined)
GAP = 2.0  # seconds of interviewer speech before each answer


def build_session(out):
    """Three answers with a 2 s gap before each. Returns (path, turns) on the recording's own clock."""
    answers = [FIX / "answer.webm", FIX / "answer2.webm", FIX / "answer.webm"]
    durations = [float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(a)],
                                      capture_output=True, text=True, check=True).stdout.strip()) for a in answers]
    inputs, filters, t, turns = [], [], 0.0, []
    for i, (a, d) in enumerate(zip(answers, durations)):
        inputs += ["-f", "lavfi", "-t", str(GAP), "-i", "anullsrc=r=16000:cl=mono", "-i", str(a)]
        turns.append({"role": "interviewer", "text": f"Question {i + 1}: tell me about a project.", "start": round(t + 0.2, 2),
                      "end": round(t + GAP - 0.2, 2)})
        t += GAP + d
    n = len(answers) * 2
    filters = "".join(f"[{k}:a]aresample=16000,aformat=channel_layouts=mono[s{k}];" for k in range(n))
    filters += "".join(f"[s{k}]" for k in range(n)) + f"concat=n={n}:v=0:a=1[out]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", filters, "-map", "[out]", out], check=True)
    return out, turns


def run_once(name, mock=False):
    from pipeline import config, session
    from pipeline.audio_metrics import analyze_audio
    from pipeline.text_metrics import analyze_text
    budget, pipelined = CONFIGS[name]
    saved = dict(config.THINKING_BUDGET)
    config.THINKING_BUDGET.update({"transcribe": budget, "interpret": budget})
    models = set()
    try:
        if mock:
            import threading, itertools
            order, lock = itertools.count(), threading.Lock()
            def call(fn):  # fake latencies: the first transcription is slow, thinking adds 0.8 s to every call
                with lock:
                    k = next(order)
                time.sleep((1.5 if k == 0 else 0.3) + (0 if budget == 0 else 0.8))
                return fn(None, "mock"), "mock"
            session.transcribe = lambda c, m, path, mime: [{"start": 0.2, "end": 2.5, "text": "I built it and cut time by half."}]
            session.interpret = lambda *a: {"score": 70, "dimensions": {"content": {"score": 70, "observation": "", "evidence": []}},
                                            "strengths": [], "improvements": [], "score_coverage": 1, "not_measured": []}
        else:
            import backend
            def call(fn):
                out, model = backend.with_client(fn)
                models.add(model)
                return out, model
        with tempfile.TemporaryDirectory() as tmp:
            path, turns = build_session(f"{tmp}/session.wav")
            audio_m = analyze_audio(path, config.MIN_PAUSE_S, config.SILENCE_DB, config.SNR_THRESHOLD_DB)
            t0, first = time.time(), None
            def emit(ev):
                nonlocal first
                if ev["type"] == "answer" and first is None:
                    first = time.time() - t0
            report = session.session_report(call, "Career", "Product intern", "resume", path, turns, audio_m, None,
                                            analyze_text, emit, pipelined=pipelined)
            total = time.time() - t0
    finally:
        config.THINKING_BUDGET.clear(); config.THINKING_BUDGET.update(saved)
    return {"config": name, "total_s": round(total, 2), "first_feedback_streamed_s": round(first or total, 2),
            "first_feedback_unstreamed_s": round(total, 2), "answers": len(report.get("answers", [])),
            "models": "+".join(sorted(models)) or "mock"}


def summary(path):
    rows = list(csv.DictReader(open(path)))
    print(f"{'config':10} {'runs':>4} {'total s':>14} {'first, no stream':>17} {'first, streamed':>16}")
    for name in CONFIGS:
        r = [x for x in rows if x["config"] == name and x["answers"] == "3"]
        if not r:
            continue
        med = lambda k: statistics.median(float(x[k]) for x in r)
        rng = lambda k: f"{min(float(x[k]) for x in r):.1f}-{max(float(x[k]) for x in r):.1f}"
        print(f"{name:10} {len(r):>4} {med('total_s'):>6.1f} ({rng('total_s'):>9}) {med('first_feedback_unstreamed_s'):>17.1f} "
              f"{med('first_feedback_streamed_s'):>16.1f}")
    others = {x["models"] for x in rows}
    print("models seen:", ", ".join(sorted(others)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", choices=list(CONFIGS) + ["each"], default="each")
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--pause", type=float, default=60.0, help="seconds between reports")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()
    out = ROOT / "eval" / ("split_timing_mock.csv" if args.mock else "split_timing.csv")
    if args.summary:
        return summary(out)
    os.environ.setdefault("MAESTRO_DATA_DIR", str(ROOT / "eval" / ".split_store"))
    if args.mock:
        os.environ.setdefault("GEMINI_API_KEY", "offline-placeholder")
    names = list(CONFIGS) if args.config == "each" else [args.config]
    plan = [n for _ in range(args.reps) for n in random.sample(names, len(names))]  # shuffled, so load drift is spread out
    for i, name in enumerate(plan):
        row = {"at": datetime.now().isoformat(timespec="seconds"), **run_once(name, args.mock)}
        print(row)
        new = not out.exists()
        with open(out, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(row))
            if new:
                w.writeheader()
            w.writerow(row)
        if i < len(plan) - 1 and not args.mock:
            time.sleep(args.pause)


if __name__ == "__main__":
    main()
