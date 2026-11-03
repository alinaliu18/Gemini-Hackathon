"""Score the live interviewer's follow-up decisions on eval/followup_cases.jsonl (45 answers, labelled by hand).

Three numbers:
  accuracy          the decision is right: "next" when nothing is missing, otherwise a follow-up about the FIRST
                    missing item (own_action, then result_number, then example)
  extra follow-ups  of the answers that needed no follow-up, the share that got one
  missed follow-ups of the answers that needed a follow-up, the share that moved on instead

  ./.venv/bin/python eval/run_followup_eval.py --rules            # offline keyword baseline, no model calls
  ./.venv/bin/python eval/run_followup_eval.py --model --pause 5  # real decider; 45 calls, one per case
  ./.venv/bin/python eval/run_followup_eval.py --model --only f01,f16

The free tier allows about 20 requests per model per key per day, so a full --model run needs a paid key or several
days with --only. Results are appended to eval/followup_results.csv with the time, mode and model.
"""
import argparse, csv, json, os, re, sys, time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CASES = ROOT / "eval" / "followup_cases.jsonl"
RESULTS = ROOT / "eval" / "followup_results.csv"

WE = re.compile(r"\b(we|our|us|the team|team's|the group|our club)\b", re.I)
I = re.compile(r"\b(I|I'm|I've|I'd|my|myself|me)\b")
NUMBER = re.compile(r"\d|\b(one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|hundred|half|double|twice)\b", re.I)
GENERAL = re.compile(r"\b(usually|always|generally|tend to|whenever|in general|i'm the kind|kind of person|often)\b", re.I)


def rules(call, question, answer, asked):
    """A keyword baseline, to know what the model has to beat."""
    missing = []
    if len(WE.findall(answer)) > len(I.findall(answer)) or not I.search(answer):
        missing.append("own_action")
    if not NUMBER.search(answer):
        missing.append("result_number")
    if GENERAL.search(answer):
        missing.append("example")
    return missing, ""


def score(rows):
    need = [r for r in rows if r["expected"] == "follow_up"]
    none = [r for r in rows if r["expected"] == "next"]
    right = sum(r["action"] == r["expected"] and (r["expected"] == "next" or r["missing"] == r["expected_first"]) for r in rows)
    return {"n": len(rows), "accuracy": right / len(rows) if rows else 0,
            "extra_followups": sum(r["action"] == "follow_up" for r in none) / len(none) if none else 0,
            "missed_followups": sum(r["action"] == "next" for r in need) / len(need) if need else 0,
            "fallbacks": sum(r["source"].endswith("fallback") for r in rows),
            "median_ms": sorted(r["ms"] for r in rows)[len(rows) // 2] if rows else 0}


def main():
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--rules", action="store_true")
    mode.add_argument("--model", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--pause", type=float, default=4.0, help="seconds between model calls")
    ap.add_argument("--timeout", type=float, default=None, help="override FOLLOWUP_TIMEOUT_S (default: the live setting)")
    args = ap.parse_args()

    os.environ.setdefault("MAESTRO_DATA_DIR", str(ROOT / "eval" / ".followup_store"))  # keep eval decisions out of data/
    if args.rules:
        os.environ.setdefault("GEMINI_API_KEY", "offline-placeholder")
    from pipeline import followup, config
    call = None
    if args.model:
        import backend
        call = backend.with_client

    cases = [json.loads(l) for l in CASES.read_text().splitlines() if l.strip()]
    if args.only:
        keep = set(args.only.split(","))
        cases = [c for c in cases if c["id"] in keep]
    rows = []
    for i, c in enumerate(cases):
        d = followup.decide(call, c["question"], c["answer"], c["followups_asked"],
                            timeout=args.timeout, decider=rules if args.rules else None,
                            source="rules" if args.rules else "model")
        rows.append({**c, **d})
        ok = d["action"] == c["expected"] and (c["expected"] == "next" or d["missing"] == c["expected_first"])
        print(f"{c['id']}  want {c['expected_first'] or 'next':14} got {d['action']}:{d['missing'] or '-':14} "
              f"{'ok ' if ok else 'BAD'} {d['source']} {d['ms']} ms")
        if args.model and i < len(cases) - 1:
            time.sleep(args.pause)
    s = score(rows)
    label = "rules" if args.rules else f"model:{config.MODEL_ID}"
    print(f"\n{label}  n={s['n']}  accuracy {s['accuracy']:.0%}  extra follow-ups {s['extra_followups']:.0%}  "
          f"missed follow-ups {s['missed_followups']:.0%}  fallbacks {s['fallbacks']}  median {s['median_ms']} ms")
    new = not RESULTS.exists()
    with open(RESULTS, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["at", "mode", "n", "accuracy", "extra_followups", "missed_followups", "fallbacks", "median_ms"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), label, s["n"], f"{s['accuracy']:.3f}",
                    f"{s['extra_followups']:.3f}", f"{s['missed_followups']:.3f}", s["fallbacks"], s["median_ms"]])


if __name__ == "__main__":
    main()
