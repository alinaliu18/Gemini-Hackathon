# Interview Maestro 🎓

An AI-powered interview preparation platform that helps users practice for academic, social, and career interviews using Google's Gemini 2.0 Flash model.

![Home Page Hints](https://img.shields.io/badge/Status-Beta-purple) ![Monet Theme](https://img.shields.io/badge/Theme-Monet-orange)

## ✨ Features
- **Multi-Track Practice**: Academic, Social, and Career interview paths.
- **AI Feedback**: Get instant scoring and detailed metrics on tone, pacing, and clarity.
- **Real-time Live Interview**: Practice with a simulated video interview interface.
- **Monet-Inspired UI**: A beautiful, calming interface designed to reduce interview anxiety.

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
- **backend.py**: Flask server handling AI connectivity.
- **public/camera.html**: Standalone Live Interview module.
- **AudioTesting/** & **CamTest/**: Legacy testing modules.

## 🛠 Troubleshooting

- **Ports**: Frontend uses `5173`, Backend uses `5002`. Ensure these ports are free.
- **API Key**: If AI feedback fails, check that your `GEMINI_API_KEY` is correct in `.env`.
- **Microphone/Camera**: Allow browser permissions for recording to work.

<img width="1307" height="730" alt="Screenshot 2026-05-29 at 23 23 24" src="https://github.com/user-attachments/assets/7ef56bfc-1791-469f-a176-cefbf03e2654" />
<img width="1302" height="732" alt="Screenshot 2026-05-29 at 23 23 46" src="https://github.com/user-attachments/assets/f8714ec9-7e53-4cc2-bba8-7f322da9b02e" />
<img width="1306" height="731" alt="Screenshot 2026-05-29 at 23 23 57" src="https://github.com/user-attachments/assets/9f3d1ce8-3b1b-4672-895d-651e76c849b0" />
<img width="1302" height="732" alt="Screenshot 2026-05-29 at 23 24 16" src="https://github.com/user-attachments/assets/5deb09cf-7067-4403-b19f-815db50e7f0b" />
<img width="1306" height="732" alt="Screenshot 2026-05-29 at 23 24 37" src="https://github.com/user-attachments/assets/703ea066-aff2-4e94-ad60-b5e1e6de5aa5" />
<img width="1301" height="733" alt="Screenshot 2026-05-29 at 23 24 52" src="https://github.com/user-attachments/assets/e0b5ee72-703c-4587-b452-a514579529af" />
<img width="1277" height="722" alt="Screenshot 2026-05-29 at 23 27 31" src="https://github.com/user-attachments/assets/1f45f0d2-cece-437c-9fff-a1a33a6d372c" />
