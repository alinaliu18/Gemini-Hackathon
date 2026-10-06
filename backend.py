import os
import io
import csv
import json
import time
import queue
import tempfile
import threading
from datetime import datetime
from pathlib import Path

import PyPDF2
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from google import genai
from google.genai import types

from pipeline import config
from pipeline.audio_metrics import analyze_audio
from pipeline.text_metrics import analyze_text
from pipeline.transcribe import transcribe
from pipeline.interpret import interpret, mmss
from pipeline.live import system_instruction, mint_token
from pipeline.session import session_report
from pipeline import store

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
TOKEN_CLIENTS = [genai.Client(api_key=k, http_options={'api_version': 'v1alpha'}) for k in API_KEYS]  # tokens are v1alpha-only


def with_client(fn):
    """Return (fn(client, model), model). 429 quota -> next key; 503 overload / 404 retired model -> next model."""
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
                if '503' in msg or 'UNAVAILABLE' in msg or '404' in msg or 'NOT_FOUND' in msg:  # overloaded or retired model
                    last = e
                    break
                raise
    raise last


def save_and_measure(audio, timings):
    """Save the uploaded recording and measure it. Returns (temp_path, audio_metrics)."""
    suffix = os.path.splitext(audio.filename or '')[1] or '.webm'
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        audio.save(f.name)
        temp_path = f.name
    t = time.time()
    audio_m = analyze_audio(temp_path, config.MIN_PAUSE_S, config.SILENCE_DB, config.SNR_THRESHOLD_DB)
    timings['audio_metrics_ms'] = int((time.time() - t) * 1000)
    return temp_path, audio_m


def read_resume():
    f = request.files.get('file')
    return extract_text_from_pdf(io.BytesIO(f.read())) if f else ""


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
    run_id = None
    timings = {}
    try:
        t0 = time.time()
        goal = (request.form.get('goal') or 'Career').strip().capitalize()  # UI sends 'career'; config keys are 'Career'
        question = request.form.get('question', '') or request.form.get('context_text', '')
        typed = request.form.get('text_input', '')
        audio = request.files.get('audio_response')
        video = json.loads(request.form['video_signals']) if request.form.get('video_signals') else None

        resume = read_resume() or "No resume provided."

        if audio:
            temp_path, audio_m = save_and_measure(audio, timings)
        run_id = store.start_run('practice', goal, request.form.get('context_text'), resume, question, typed, video=video,
                                 audio_src=temp_path, audio_mime=audio.mimetype if audio else None)  # input saved before any model call
        if audio:
            t = time.time()
            segments, timings['transcribe_model'] = with_client(
                lambda c, m: transcribe(c, m, temp_path, audio.mimetype or 'audio/webm'))
            timings['transcribe_ms'] = int((time.time() - t) * 1000)
        else:
            audio_m = NO_AUDIO
            segments = [{"start": 0.0, "end": 0.0, "text": typed}] if typed.strip() else []
        if not segments and typed.strip():  # recording came back empty: grade the typed answer instead
            segments, audio_m = [{"start": 0.0, "end": 0.0, "text": typed}], NO_AUDIO
        if not segments:
            app.logger.warning("empty transcript: speech_s=%s noisy=%s", audio_m.get("speech_s"), audio_m.get("noisy"))
            msg = ("We couldn't hear any speech in the recording. Check that your microphone is on and not in use "
                   "by another tab, then record again or type your answer.") if audio and not audio_m.get("speech_s") \
                else "No speech detected. Please record or type an answer."
            store.finish_run(run_id, error=msg, timings=timings)
            return jsonify({"score": 0, "evaluation": msg, "metrics": {}}), 400

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
        store.finish_run(run_id, report=result, timings=timings)
        return jsonify(result)
    except Exception as e:
        app.logger.exception("evaluate failed")
        if run_id:
            store.finish_run(run_id, error=e, timings=timings)
        return jsonify({"score": 0, "evaluation": f"Backend Error: {e}", "metrics": {}}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


QUESTION_PROMPT = """You are a {track} interviewer preparing one question for a mock interview.
Resume (may be empty):
{resume}
Context from the candidate (may be empty): {context}
Write ONE interview question. It must name a specific item from the resume (a project, job, number or skill) and ask what
the candidate decided and why, or how they handled a trade-off or setback. If the resume is empty, use the context; if both
are empty, ask a common {track} question. Do not repeat any of these: {avoid}
Return only the question, one or two sentences."""


@app.route('/api/question', methods=['POST'])
def question_route():
    """One resume-based question for Quick Practice."""
    goal = (request.form.get('goal') or 'Career').strip().capitalize()
    prompt = QUESTION_PROMPT.format(track=goal.lower(), resume=(read_resume() or "(none)")[:6000],
                                    context=request.form.get('context_text', '') or "(none)",
                                    avoid=request.form.get('avoid', '') or "(none)")
    try:
        text, _ = with_client(lambda c, m: c.models.generate_content(model=m, contents=prompt,
                                                                     config={"temperature": 0.9}).text)
        return jsonify({"question": text.strip().strip('"')})
    except Exception as e:
        app.logger.exception("question failed")
        return jsonify({"error": str(e)}), 500


@app.route('/api/live/token', methods=['POST'])
def live_token():
    """Mint a one-use Live API token with the interviewer's instructions (built from the resume) locked in."""
    goal = (request.form.get('goal') or 'Career').strip().capitalize()
    instruction = system_instruction(goal, read_resume(), request.form.get('context_text', ''))
    last = None
    for client in TOKEN_CLIENTS:
        try:
            return jsonify({"token": mint_token(client, config.LIVE_MODEL, instruction), "model": config.LIVE_MODEL})
        except Exception as e:
            if '429' in str(e) or 'RESOURCE_EXHAUSTED' in str(e):
                last = e
                continue
            app.logger.exception("token failed")
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": str(last)}), 429


def build_report(audio, goal, context, turns, video, resume, emit=None):
    """Run the whole-interview pipeline on an uploaded recording. Returns the finished report dict."""
    timings = {}
    t0 = time.time()
    temp_path, audio_m = save_and_measure(audio, timings)
    run_id = store.start_run('live', goal, context, resume, turns=turns, video=video, audio_src=temp_path,
                             audio_mime=getattr(audio, 'mimetype', None))  # the input is saved before any model call
    try:
        report = session_report(with_client, goal, context, resume, temp_path, turns, audio_m, video, analyze_text, emit)
    except Exception as e:
        store.finish_run(run_id, error=e, timings=timings)
        raise
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    timings['total_ms'] = int((time.time() - t0) * 1000)
    report.update({"transcript": [{**s, "t": mmss(s["start"])} for s in report.pop("segments")], "turns": turns,
                   "signals": {"audio": audio_m, "video": video}, "timings": timings, "run_id": run_id})
    store.finish_run(run_id, report=report, timings=timings)
    return report


def report_inputs():
    goal = (request.form.get('goal') or 'Career').strip().capitalize()
    turns = json.loads(request.form.get('turns') or '[]')
    video = json.loads(request.form['video_signals']) if request.form.get('video_signals') else None
    return goal, request.form.get('context_text', ''), turns, video, read_resume() or "No resume provided."


@app.route('/api/session_report', methods=['POST'])
def session_report_route():
    """Report for a whole live interview: the candidate's recording + the interviewer's turns (+ on-device video numbers)."""
    try:
        audio = request.files.get('audio_response')
        if not audio:
            return jsonify({"error": "No recording uploaded."}), 400
        goal, context, turns, video, resume = report_inputs()
        return jsonify(build_report(audio, goal, context, turns, video, resume))
    except Exception as e:
        app.logger.exception("session report failed")
        return jsonify({"error": f"Backend Error: {e}"}), 500


@app.route('/api/session_report/stream', methods=['POST'])
def session_report_stream_route():
    """Same report, sent as it is built: one JSON object per line (stage, transcribed, answer, summary), then
    {"type": "done", "report": ...} with the finished report, or {"type": "error", ...}."""
    audio = request.files.get('audio_response')
    if not audio:
        return jsonify({"error": "No recording uploaded."}), 400
    try:
        goal, context, turns, video, resume = report_inputs()
    except Exception as e:
        return jsonify({"error": f"Bad request: {e}"}), 400
    events = queue.Queue()
    # Save the upload before the response starts: the request's files are gone once the view returns.
    path = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio.filename or '')[1] or '.webm')
    audio.save(path.name)
    path.close()

    class Saved:  # lets build_report keep one code path for the plain and the streaming route
        filename = path.name
        def save(self, dest):
            os.replace(path.name, dest)

    def run():
        try:
            events.put({"type": "done", "report": build_report(Saved(), goal, context, turns, video, resume, events.put)})
        except Exception as e:
            app.logger.exception("session report stream failed")
            events.put({"type": "error", "error": f"Backend Error: {e}"})
        finally:
            if os.path.exists(path.name):
                os.remove(path.name)
            events.put(None)

    threading.Thread(target=run, daemon=True).start()

    def lines():
        while (ev := events.get()) is not None:
            yield json.dumps(ev) + "\n"

    return Response(lines(), mimetype='application/x-ndjson', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


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
