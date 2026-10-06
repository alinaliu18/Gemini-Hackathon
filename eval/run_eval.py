#!/usr/bin/env python
"""Offline eval harness: app scores vs human ratings. See eval/README.md."""
import argparse
import csv
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
import backend  # noqa: E402

DIMS = ["content", "structure", "clarity", "pacing", "filler_words"]
MIMES = {".webm": "audio/webm", ".wav": "audio/wav", ".m4a": "audio/mp4", ".mp3": "audio/mpeg"}
EMOTION_RE = re.compile(r"nervous|anxious|not confident|lack of confidence|紧张|不自信", re.I)
SMILE_RE = re.compile(r"smil(?:e|ing)|laugh", re.I)


def resolve_audio(path):
    if os.path.isfile(path):
        return path
    alt = os.path.join(REPO, "eval", "data", "audio", path)
    if os.path.isfile(alt):
        return alt
    return os.path.join(REPO, path)


def evaluate_row(audio_path, goal, question):
    mime = MIMES.get(os.path.splitext(audio_path)[1].lower(), "audio/webm")
    form = {"goal": goal, "question": question}
    sidecar = os.path.splitext(audio_path)[0] + ".json"
    if os.path.isfile(sidecar):
        with open(sidecar, encoding="utf-8") as f:
            form["video_signals"] = f.read()
    with open(audio_path, "rb") as f:
        resp = backend.app.test_client().post(
            "/api/evaluate", data={**form, "audio_response": (f, os.path.basename(audio_path), mime)},
            content_type="multipart/form-data")
    if resp.status_code != 200:
        raise RuntimeError(f"{audio_path}: HTTP {resp.status_code}: {resp.get_data(as_text=True)[:200]}")
    return resp.get_json()


# --- rules: each takes the app response JSON, returns bool ---

def rule_clarity_null_when_noisy(r):
    return not (r["signals"]["audio"]["noisy"] and r["dimensions"]["clarity"]["score"] is not None)


def rule_no_emotion_words(r):
    blob = json.dumps([r["dimensions"], r["strengths"], r["improvements"], r["congruence"]],
                      ensure_ascii=False)
    return not EMOTION_RE.search(blob)


def rule_every_item_has_evidence(r):
    items = r["strengths"] + r["improvements"]
    return all(i.get("evidence") for i in items)


def rule_smile_not_penalized(r):
    return not any(SMILE_RE.search(i["text"]) for i in r["improvements"])


RULES = {"clarity_null_when_noisy": rule_clarity_null_when_noisy,
         "no_emotion_words": rule_no_emotion_words,
         "every_item_has_evidence": rule_every_item_has_evidence,
         "smile_not_penalized": rule_smile_not_penalized}


def num(v):
    return float(v) if v not in (None, "") else None  # empty cell = not rated


def mae(pairs):
    pairs = [(a, h) for a, h in pairs if a is not None and h is not None]
    if not pairs:
        return None, 0
    return sum(abs(a - h) for a, h in pairs) / len(pairs), len(pairs)


def run(labels_path, report_path):
    with open(labels_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    dim_pairs = {d: [] for d in DIMS + ["total"]}
    rule_rows, latency_rows = [], []
    for row in rows:
        name = os.path.basename(row["file"])
        resp = evaluate_row(resolve_audio(row["file"]), row["goal"], row["question"])
        for d in DIMS:
            dim_pairs[d].append((resp["dimensions"][d]["score"], num(row.get(f"human_{d}"))))
        dim_pairs["total"].append((resp["score"], num(row.get("human_total"))))
        rule_rows.append((name, {rn: RULES[rn](resp) for rn in (row.get("expect") or "").split(";") if rn}))
        latency_rows.append((name, resp["timings"].get("total_ms")))

    lines = ["# Eval report\n", "## MAE vs human\n", "| dimension | MAE | n |", "|---|---|---|"]
    for d in DIMS + ["total"]:
        m, n = mae(dim_pairs[d])
        lines.append(f"| {d} | {m:.1f} | {n} |" if m is not None else f"| {d} | - | 0 |")
    lines += ["\n## Rules\n", "| file | rule | result |", "|---|---|---|"]
    for name, checks in rule_rows:
        for rn, ok in checks.items():
            lines.append(f"| {name} | {rn} | {'PASS' if ok else 'FAIL'} |")
    lines += ["\n## Latency (total_ms)\n", "| file | total_ms |", "|---|---|"]
    lines += [f"| {n} | {ms} |" for n, ms in latency_rows]

    report = "\n".join(lines) + "\n"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)


def selftest():
    assert num("") is None and num(None) is None and num("80") == 80.0
    assert mae([(80, None), (70, 60.0)]) == (10.0, 1)
    noisy = {"dimensions": {"clarity": {"score": None}}, "strengths": [], "improvements": [], "congruence": []}
    noisy["signals"] = {"audio": {"noisy": True}}
    assert rule_clarity_null_when_noisy(noisy)
    noisy["dimensions"]["clarity"]["score"] = 80
    assert not rule_clarity_null_when_noisy(noisy)
    clean = {"signals": {"audio": {"noisy": False}}, "dimensions": {"clarity": {"score": 80}},
             "strengths": [], "improvements": [], "congruence": []}
    assert rule_clarity_null_when_noisy(clean)

    emo = {"dimensions": {}, "strengths": [], "improvements": [{"text": "you seem nervous", "evidence": []}],
           "congruence": []}
    assert not rule_no_emotion_words(emo)
    emo["improvements"][0]["text"] = " Good pace. "
    assert rule_no_emotion_words(emo)
    assert not rule_no_emotion_words({"dimensions": {}, "strengths": [], "improvements": [],
                                      "congruence": [{"text": "有点不自信"}]})

    no_ev = {"strengths": [{"text": "a", "evidence": []}], "improvements": [{"text": "b", "evidence": ["x"]}]}
    assert not rule_every_item_has_evidence(no_ev)
    no_ev["strengths"][0]["evidence"] = ["y"]
    assert rule_every_item_has_evidence(no_ev)

    smile = {"strengths": [], "improvements": [{"text": "try smiling more", "evidence": []}]}
    assert not rule_smile_not_penalized(smile)
    assert rule_smile_not_penalized({"strengths": [], "improvements": []})

    assert mae([(80, 85), (90, 85), (None, 85)]) == (5.0, 2)
    assert mae([]) == (None, 0)
    print("SELFTEST OK")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", action="store_true", help="use eval/sample_labels.csv instead of eval/data/labels.csv")
    ap.add_argument("--selftest", action="store_true", help="run offline checks on fake responses and exit")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        sys.exit(0)
    labels = os.path.join(REPO, "eval", "sample_labels.csv" if args.sample else os.path.join("data", "labels.csv"))
    if not os.path.isfile(labels):
        sys.exit(f"No labels at {labels}\n"
                 "Create eval/data/labels.csv (see eval/README.md) or run with --sample.")
    run(labels, os.path.join(REPO, "eval", "report.md"))
