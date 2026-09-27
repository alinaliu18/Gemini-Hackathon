import os
import io
import csv
import json
import time
import tempfile
from datetime import datetime
from pathlib import Path

import PyPDF2
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types

from pipeline import config
from pipeline.audio_metrics import analyze_audio
from pipeline.text_metrics import analyze_text
from pipeline.transcribe import transcribe
from pipeline.interpret import interpret, mmss

# ---------- load .env ----------
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"]}})

# ---------- Gemini (rotate keys on quota errors, fall back to another model on overload) ----------
API_KEYS = [k for k in os.environ.get('GEMINI_API_KEYS', '').split(',') if k] or \
           [os.environ.get('GEMINI_API_KEY', '')]
if not API_KEYS[0]:
    raise ValueError("Set GEMINI_API_KEY (or GEMINI_API_KEYS=key1,key2) in .env")
# The SDK's default retry backs off for ~2 min on 503; retry once, then let with_client switch model.
CLIENTS = [genai.Client(api_key=k, http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=2)))
           for k in API_KEYS]


def with_client(fn):
    """Return (fn(client, model), model). 429 quota -> next key; 503 overload -> next model."""
    last = None
    for model in [config.MODEL_ID, *config.FALLBACK_MODELS]:
        for client in CLIENTS:
            try:
                return fn(client, model), model
            except Exception as e:  # google-genai raises APIError subclasses; match on the status text
                msg = str(e)
                if '429' in msg or 'RESOURCE_EXHAUSTED' in msg:
                    last = e
                    continue
                if '503' in msg or 'UNAVAILABLE' in msg:
                    last = e
                    break
                raise
    raise last


def extract_text_from_pdf(pdf_file):
    try:
        return "".join(page.extract_text() or "" for page in PyPDF2.PdfReader(pdf_file).pages)
    except Exception as e:
        return f"Could not read PDF: {e}"


NO_AUDIO = {"duration_s": 0, "speech_s": 0, "pauses": [], "long_pause_count": 0,
            "noise_db": None, "speech_db": None, "snr_db": None, "noisy": False}


def legacy_view(result):
    """Keep the fields the current UI renders (score / evaluation / metrics) while adding the evidence-based ones."""
    def ev_str(ev):
        return "; ".join(f"{e['t']} " + (f'"{e["quote"]}"' if e.get("quote") else e.get("signal", "")) for e in ev[:2])
    metrics = {}
    for name, d in result["dimensions"].items():
        score = "—" if d["score"] is None else d["score"]
        metrics[name] = f"{score} · {d['observation']}" + (f" ({ev_str(d['evidence'])})" if d["evidence"] else "")
    parts = ["What went well: " + " ".join(s["text"] for s in result["strengths"])] if result["strengths"] else []
    parts += ["To work on: " + " ".join(f"{i['text']} Tip: {i.get('tip', '')}" for i in result["improvements"])] if result["improvements"] else []
    if result.get("score_coverage", 1) < 0.8:
        parts.insert(0, f"Partial score: based on {result['score_coverage']:.0%} of the rubric "
                        f"({', '.join(result['not_measured'])} could not be measured).")
    return {"score": result["score"] if result["score"] is not None else 0,
            "evaluation": "\n".join(parts) or "Not enough evidence to give feedback. Try a longer answer.",
            "metrics": metrics}


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "Backend is running!", "port": 5002})


@app.route('/api/evaluate', methods=['POST', 'OPTIONS'])
def evaluate_interview():
    if request.method == 'OPTIONS':
        return '', 200
    temp_path = None
    timings = {}
    try:
        t0 = time.time()
        goal = (request.form.get('goal') or 'Career').strip().capitalize()  # UI sends 'career'; config keys are 'Career'
        question = request.form.get('question', '') or request.form.get('context_text', '')
        typed = request.form.get('text_input', '')
        audio = request.files.get('audio_response')
        video = json.loads(request.form['video_signals']) if request.form.get('video_signals') else None

        resume = "No resume provided."
        if request.files.get('file'):
            resume = extract_text_from_pdf(io.BytesIO(request.files['file'].read()))

        if audio:
            suffix = os.path.splitext(audio.filename or '')[1] or '.webm'
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                audio.save(f.name)
                temp_path = f.name
            t = time.time()
            audio_m = analyze_audio(temp_path, config.MIN_PAUSE_S, config.SILENCE_DB, config.SNR_THRESHOLD_DB)
            timings['audio_metrics_ms'] = int((time.time() - t) * 1000)
            t = time.time()
            segments, timings['transcribe_model'] = with_client(
                lambda c, m: transcribe(c, m, temp_path, audio.mimetype or 'audio/webm'))
            timings['transcribe_ms'] = int((time.time() - t) * 1000)
        else:
            audio_m = NO_AUDIO
            segments = [{"start": 0.0, "end": 0.0, "text": typed}] if typed.strip() else []
        if not segments:
            return jsonify({"score": 0, "evaluation": "No speech detected. Please record or type an answer.", "metrics": {}}), 400

        # In noisy audio silence detection fails, so speech time is unknown: fall back to transcript timestamps.
        text_m = analyze_text(segments, None if audio_m["noisy"] else (audio_m["speech_s"] or None))
        t = time.time()
        result, timings['interpret_model'] = with_client(
            lambda c, m: interpret(c, m, question, goal, resume, segments, audio_m, text_m, video))
        timings['interpret_ms'] = int((time.time() - t) * 1000)
        timings['total_ms'] = int((time.time() - t0) * 1000)

        result.update({"transcript": [{**s, "t": mmss(s["start"])} for s in segments],
                       "signals": {"audio": audio_m, "text": text_m, "video": video},
                       "timings": timings})
        result.update(legacy_view(result))
        log_run(goal, result, timings)
        return jsonify(result)
    except Exception as e:
        app.logger.exception("evaluate failed")
        return jsonify({"score": 0, "evaluation": f"Backend Error: {e}", "metrics": {}}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def log_run(goal, result, timings):
    """Append one row per evaluation so latency and score drift can be tracked over time."""
    log_file = Path(__file__).parent / 'eval_log.csv'
    new = not log_file.exists() or log_file.stat().st_size == 0
    with open(log_file, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['timestamp', 'goal', 'score', 'total_ms', 'transcribe_ms', 'interpret_ms', 'dropped_items', 'dimension_scores'])
        w.writerow([datetime.now().isoformat(), goal, result.get('score'), timings.get('total_ms'),
                    timings.get('transcribe_ms'), timings.get('interpret_ms'), len(result.get('dropped', [])),
                    json.dumps({k: v['score'] for k, v in result['dimensions'].items()})])


if __name__ == '__main__':
    app.run(debug=False, use_reloader=False, port=5002, host='127.0.0.1')
