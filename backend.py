import os
import json
import io
import csv
from datetime import datetime
import tempfile

import PyPDF2
from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from pathlib import Path

# ---------- load .env ----------
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                val = val.strip().strip('"').strip("'")
                os.environ.setdefault(key.strip(), val)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"]}})

# ---------- Gemini  ----------
api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable not set. Add it to .env file or export it.")
client = genai.Client(api_key=api_key)
MODEL_ID = "gemini-2.5-flash"

# ---------- help func ----------
def extract_text_from_pdf(pdf_file):
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content
        return text
    except Exception as e:
        return f"Could not read PDF: {str(e)}"

# ---------- health check ----------
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "Backend is running!", "port": 5002})

# ---------- eval ----------
@app.route('/api/evaluate', methods=['POST', 'OPTIONS'])
def evaluate_interview():
    if request.method == 'OPTIONS':
        return '', 200

    temp_path = None
    try:
        import time
        start_time = time.time()
        goal = request.form.get('goal', 'General')
        sub_type = request.form.get('sub_type', 'Interview')
        user_response = request.form.get('text_input', '')
        context_text = request.form.get('context_text', '')
        audio_response = request.files.get('audio_response')

        resume_content = "No resume provided."
        uploaded_file = request.files.get('file')
        if uploaded_file:
            pdf_stream = io.BytesIO(uploaded_file.read())
            resume_content = extract_text_from_pdf(pdf_stream)

        # track
        track_focus = {
            "Academic": "Focus on clarity of research explanation, logical structure, enthusiasm. Weight: clarity 40%, confidence 30%, professionalism 30%.",
            "Social": "Focus on friendliness, empathy, conversational flow. Weight: engagement 40%, tone 30%, pacing 30%.",
            "Career": "Focus on professionalism, relevant experience, problem-solving. Weight: professionalism 40%, confidence 30%, clarity 30%."
        }
        focus_text = track_focus.get(goal, track_focus["Career"])

        prompt = f"""
        You are an expert interview coach for {goal} ({sub_type}).
        {focus_text}
        RESUME: {resume_content}
        CONTEXT/NOTES: {context_text}
        USER RESPONSE: "{user_response}"

        TASK: 
        1. Analyze the audio response based on the position requested.
        2. Evaluate speech patterns: pacing, tone, filler words, stutters.
        3. Assess other soft qualities: confidence, clarity, engagement, professionalism.
        4. Provide a total score (0-100) and detailed evaluation.
        Return ONLY a JSON object with this structure: 
        {{
          "score": 0-100,
          "evaluation": "string",
          "metrics": {{
            "filler_word_count": "string",
            "tone_analysis": "string",
            "pacing": "string",
            "confidence": "string",
            "clarity": "string",
            "stutters": "string",
            "engagement": "string",
            "professionalism": "string",
            "additional_qualities": "string"
          }}
        }}
        """

        contents = [prompt]

        if audio_response:
            suffix = os.path.splitext(audio_response.filename)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_audio_file:
                audio_response.save(temp_audio_file.name)
                temp_path = temp_audio_file.name

            uploaded_audio = client.files.upload(file=temp_path, config={'mime_type': audio_response.mimetype})
            contents.append(uploaded_audio)

        response = client.models.generate_content(
            model=MODEL_ID,
            contents=contents,
            config=genai.types.GenerateContentConfig(response_mime_type='application/json')
        )

        raw_text = response.text
        clean_text = raw_text.replace('```json', '').replace('```', '').strip()
        ai_data = json.loads(clean_text)
        latency_ms = int((time.time() - start_time) * 1000)
        
        # ---------- CSV ----------
        log_file = os.path.join(os.path.dirname(__file__), 'eval_log.csv')
        file_exists = os.path.isfile(log_file)
        with open(log_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['timestamp', 'goal', 'sub_type', 'response_len', 'score', 'latency_ms', 'metrics_summary'])
            writer.writerow([
                datetime.now().isoformat(),
                goal,
                sub_type,
                len(user_response),
                ai_data.get('score'),
                latency_ms,
                json.dumps(ai_data.get('metrics', {}))[:200]
            ])
        # ----------------------------------------

        return jsonify(ai_data)

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"score": 0, "evaluation": f"Backend Error: {str(e)}"}), 500

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == '__main__':
    app.run(debug=False, use_reloader=False, port=5002, host='127.0.0.1')
