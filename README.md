# Interview Maestro

An evidence-based interview practice tool. Record an answer, get feedback where every point points to a timestamp and a quote or a measured signal. Powered by gemini-2.5-flash (config in pipeline/config.py, fallbacks: gemini-flash-latest then gemini-2.5-flash-lite).

![Home Page Hints](https://img.shields.io/badge/Status-Beta-purple) ![Monet Theme](https://img.shields.io/badge/Theme-Monet-orange)

## Features
- Multi-track practice: Academic, Social, Career interview paths.
- Evidence-based feedback: every item cites a timestamp plus a transcript quote or a measured signal.
- Standalone camera practice page (`public/camera.html`); not yet a live, back-and-forth interviewer.
- Face signals measured in the browser; video never leaves the device.

## What problem this solves

People practicing interviews get vague AI feedback like "be more confident". They cannot check where it came from or what to change. Many tools also guess emotions from the face, which is unreliable.

This tool takes a different approach.

## How it works

**What can be measured is measured in code. Gemini only interprets content.**

Measured in code:
- Speaking pace: words per minute, compared to a per-track band.
- Pauses: ffmpeg silencedetect; pauses of 3 seconds or more are surfaced.
- Filler words: um, uh, you know, "like,", 嗯, 呃, and similar.
- Background noise: signal-to-noise ratio (SNR).
- Eye contact and face-in-frame: measured from the camera.

Interpreted by Gemini: content, structure (STAR), clarity, presence.

**Evidence rule.** Every feedback item must cite a timestamp plus either a verbatim quote from the transcript or a measured signal. Quotes are checked against the transcript in code. Items with fabricated quotes or no evidence are dropped. Clicking a timestamp in the results jumps the recording to that moment.

**No emotion inference.** Words like "nervous" or "not confident" are filtered out in code. Smiling is never counted against the user.

**Noisy audio.** If SNR is below 15 dB, clarity is not scored and pauses are not judged (noise hides silences). Pace is estimated from transcript timestamps instead.

**Camera.** MediaPipe Face Landmarker runs in the browser. Video never leaves the device; only numbers are sent (for example "facing camera 72%", look-away moments). If the face is in frame less than 50% of the time, eye contact and presence are marked "not measured" instead of scored low.

**Score.** A track-weighted average (Academic / Social / Career weights) over the dimensions that could be measured. If less than 80% of the rubric weight was measurable, the UI shows "Partial score" and lists what was not measured.

**Reliability.** 429 quota errors rotate to the next API key; 503 overload switches to a fallback model. SDK retries are capped so the user is not left waiting minutes. Audio is sent inline (no upload round trip) when under 15 MB.

## Testing and evaluation

```bash
./.venv/bin/python tests/test_interpret.py   # offline: evidence, emotion filter, scoring rules
./.venv/bin/python tests/test_metrics.py     # offline: pauses, noise, fillers
./.venv/bin/python tests/test_fallback.py    # offline: key rotation / model fallback
./.venv/bin/python tests/e2e_smoke.py        # real Gemini calls, uses tests/fixtures
node src/signals/aggregate.test.mjs
node src/signals/faceSignals.test.mjs
./.venv/bin/python eval/run_eval.py --selftest   # offline
./.venv/bin/python eval/run_eval.py --sample     # real API; see eval/README.md for adding human-rated recordings
```

Current results:
- eval --sample on the two synthetic fixtures: 5/5 rule checks PASS; end-to-end latency 25-31 s per answer.
- A browser-recorded answer replayed against the backend (with camera signals): 33-46 s end to end. The full browser flow (record -> upload -> results page with clickable timestamps) was run headless with a simulated mic/camera.
- Transcription with inline audio: 4-10 s.

## Known limitations

- Gemini transcription sometimes drops filler words despite instructions, so fillers can be undercounted.
- "Eye contact" is head pose (facing the camera), not true eye tracking.
- No human-rated recordings yet, so agreement with human scores (MAE) has not been measured; thresholds and weights in pipeline/config.py are initial assumptions to calibrate.
- Feedback takes about 30 s per answer.
- The test fixtures are synthetic (macOS text-to-speech), not real candidates.

## Credits

The original camera/live-interview prototype (public/camera.html) was built by a teammate during the hackathon; the evidence-based pipeline was added in the multimodal-upgrade branch.

## 🚀 Getting Started

Follow these steps to set up the project locally.

### Prerequisites
- **Node.js** (v16+)
- **Python** (v3.9+) or **Conda**

### 1. Installation

**Frontend Setup**
```bash
# Install Node dependencies
npm install
```


**Backend Setup**
You can use either Conda or Pip.

*Option A: Conda (Recommended)*
```bash
# Create and activate environment
conda env create -f environment.yml
conda activate Gemini
```

*Option B: Pip*
```bash
# Install requirements
pip install -r requirements.txt
```

### 2. Configuration (Crucial!)

1. Create a `.env` file in the root directory.
2. Add your Google Gemini API key:
   ```env
   GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
   ```
   Optional: provide multiple keys for rotation on quota errors:
   ```env
   GEMINI_API_KEYS=key1,key2,key3
   ```
   *(Note: You can duplicate `.env.example` and rename it to `.env`)*

---

## ▶️ Running the App

You need two terminal windows running simultaneously.

**Terminal 1: Start Backend**
```bash
# Make sure your python environment is activated
python backend.py
```
*Backend runs on http://localhost:5002*

**Terminal 2: Start Frontend**
```bash
npm run dev
```
*Frontend runs on http://localhost:5173*

Open **http://localhost:5173** in your browser to begin!

---

## 🌍 Public Deployment (GitHub Pages)

This repo is configured to deploy automatically to GitHub Pages when changes are pushed to the `main` branch. After the workflow completes, the live site will be available at:

**https://fushanbobfan.github.io/Gemini-Hackathon/**

If you fork the repo, update the `base` path in `vite.config.js` and use the corresponding GitHub Pages URL for your account.

### ✅ One-time setup on GitHub
1. Push this branch (`main`) to GitHub.
2. In the GitHub repo, go to **Settings → Pages**.
3. Under **Build and deployment**, set **Source** to **GitHub Actions**.

### 🚀 Deploy (every time you want a new build)
1. Commit and push changes to the `main` branch.
2. Wait for **Actions → Deploy to GitHub Pages** to finish.
3. Open the live URL: **https://fushanbobfan.github.io/Gemini-Hackathon/**

---

## 📂 Project Structure

- **src/**: React frontend source code.
  - `App.jsx`: Main application logic and routing.
  - `App.css`: All styling (Monet theme, animations).
  - `src/signals/`: Browser-side face measurement (`faceSignals.js`, `aggregate.js`).
  - `src/components/EvidenceFeedback.jsx`: Evidence-based feedback display.
- **pipeline/**: Evaluation pipeline.
  - `config.py`: Model, thresholds, and track weights.
  - `transcribe.py`: Transcription.
  - `audio_metrics.py`: Pauses and noise (SNR).
  - `text_metrics.py`: Pace and filler words.
  - `interpret.py`: Gemini interpretation and evidence checks.
- **tests/**: Offline and smoke tests.
- **eval/**: Evaluation runner and fixtures (`eval/README.md`).
- **backend.py**: Flask server handling AI connectivity.
- **public/camera.html**: Standalone Live Interview module.
- **AudioTesting/** & **CamTest/**: Legacy testing modules.

## 🛠 Troubleshooting

- **Ports**: Frontend uses `5173`, Backend uses `5002`. Ensure these ports are free.
- **API Key**: If AI feedback fails, check that your `GEMINI_API_KEY` is correct in `.env`.
- **Microphone/Camera**: Allow browser permissions for recording to work.
- **ffmpeg**: Must be installed and on your PATH. Pause detection uses ffmpeg silencedetect.

<img width="1307" height="730" alt="Screenshot 2026-05-29 at 23 23 24" src="https://github.com/user-attachments/assets/7ef56bfc-1791-469f-a176-cefbf03e2654" />
<img width="1302" height="732" alt="Screenshot 2026-05-29 at 23 23 46" src="https://github.com/user-attachments/assets/f8714ec9-7e53-4cc2-bba8-7f322da9b02e" />
<img width="1306" height="731" alt="Screenshot 2026-05-29 at 23 23 57" src="https://github.com/user-attachments/assets/9f3d1ce8-3b1b-4672-895d-651e76c849b0" />
<img width="1302" height="732" alt="Screenshot 2026-05-29 at 23 24 16" src="https://github.com/user-attachments/assets/5deb09cf-7067-4403-b19f-815db50e7f0b" />
<img width="1306" height="732" alt="Screenshot 2026-05-29 at 23 24 37" src="https://github.com/user-attachments/assets/703ea066-aff2-4e94-ad60-b5e1e6de5aa5" />
<img width="1301" height="733" alt="Screenshot 2026-05-29 at 23 24 52" src="https://github.com/user-attachments/assets/e0b5ee72-703c-4587-b452-a514579529af" />
<img width="1277" height="722" alt="Screenshot 2026-05-29 at 23 27 31" src="https://github.com/user-attachments/assets/1f45f0d2-cece-437c-9fff-a1a33a6d372c" />
