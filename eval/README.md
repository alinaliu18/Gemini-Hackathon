# Offline eval harness

Compares the app's scores against your own human ratings, using the real
pipeline end to end (this calls the paid API).

## Setup

- Put audio files in `eval/data/audio/` and your ratings in `eval/data/labels.csv`.
  Both are gitignored — recordings of real people never go in git.
- `labels.csv` columns:
  `file,goal,question,human_total,human_content,human_structure,human_clarity,human_pacing,human_filler_words,expect`
  - `file`: path relative to repo root, or a filename inside `eval/data/audio/`.
  - Human scores: leave a column empty to skip that dimension for this file.
  - `expect` (optional): `;`-separated rule names that must hold. Rules:
    `clarity_null_when_noisy`, `no_emotion_words`, `every_item_has_evidence`, `smile_not_penalized`.

## Run

```
./.venv/bin/python eval/run_eval.py            # real data, real API calls
./.venv/bin/python eval/run_eval.py --sample   # rule checks on the two synthetic fixtures (no human scores), still costs API calls
```

Writes `eval/report.md` (fine to commit) and prints the same summary.
If a JSON file with the same stem sits next to the audio (e.g. `answer.json`),
it is sent as the `video_signals` form field.
