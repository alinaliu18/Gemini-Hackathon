import React, { useRef, useState } from 'react';
import './App.css';
import LiveInterview from './components/LiveInterview';
import SessionReport from './components/SessionReport';
import Landing from './screens/Landing';
import Setup from './screens/Setup';
import QuickPractice from './screens/QuickPractice';

const API_BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:5002';

// Main path: landing -> setup -> live -> report. Quick Practice ('practice') is only reachable from the landing link.
function App() {
  // #setup opens Setup directly (handy for screenshots and sharing); every other screen needs state from earlier ones.
  const [screen, setScreen] = useState(() => (window.location.hash === '#setup' ? 'setup' : 'landing')); // landing | setup | live | report | practice

  // Shared inputs: Setup fills them, the live interview and Quick Practice send them to the backend.
  const [interviewGoal, setInterviewGoal] = useState('');
  const [resumeFile, setResumeFile] = useState(null);
  const [contextText, setContextText] = useState('');

  // The live interview's report: {report, audioURL, progress, streaming, error}. It starts empty and fills in as results stream in.
  const [session, setSession] = useState(null);
  const run = useRef({ id: 0, form: null, audioURL: null });

  async function startReport(fd, audioURL) {
    const id = ++run.current.id;
    run.current.form = fd; run.current.audioURL = audioURL;
    const update = (fn) => { if (run.current.id === id) setSession((s) => (s ? fn(s) : s)); };
    setSession({ audioURL, report: { summary: null, answers: [], transcript: [] }, progress: { done: 0, total: 0 }, streaming: true, error: null });
    setScreen('report');
    const handle = (ev) => {
      if (ev.type === 'stage') update((s) => ({ ...s, progress: { ...s.progress, total: ev.total } }));
      else if (ev.type === 'transcribed') update((s) => ({ ...s, progress: { done: ev.done, total: ev.total } }));
      else if (ev.type === 'answer') update((s) => ({ ...s, report: { ...s.report, answers: [...s.report.answers, ev.answer].sort((a, b) => a.asked_at - b.asked_at) } }));
      else if (ev.type === 'summary') update((s) => ({ ...s, report: { ...s.report, summary: ev.summary } }));
      else if (ev.type === 'done') update((s) => ({ ...s, report: ev.report, streaming: false }));
      else if (ev.type === 'error') throw new Error(ev.error);
    };
    try {
      const res = await fetch(`${API_BASE_URL}/api/session_report/stream`, { method: 'POST', body: fd });
      if (!res.ok || !res.body) throw new Error((await res.json().catch(() => ({}))).error || `Report failed (${res.status})`);
      const reader = res.body.getReader(); const decoder = new TextDecoder();
      let buf = '', finished = false;
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        for (let i = buf.indexOf('\n'); i >= 0; i = buf.indexOf('\n')) {
          const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
          if (line) { const ev = JSON.parse(line); finished = finished || ev.type === 'done'; handle(ev); }
        }
      }
      if (!finished) throw new Error('The connection closed before the report was finished.');
    } catch (e) {
      // "Failed to fetch" means the backend is not reachable.
      update((s) => ({ ...s, streaming: false, error: e instanceof TypeError ? "Can't reach the backend. Start it with `npm start`, then try again." : e.message }));
    }
  }

  // Dev only (stripped from production builds): lets tests open the report screen without a live interview.
  if (import.meta.env.DEV) window.__startReport = startReport;

  return (
    <div className="app">
      {screen === 'landing' && <Landing onStart={() => setScreen('setup')} onPractice={() => setScreen('practice')} />}

      {screen === 'setup' && (
        <Setup goal={interviewGoal} setGoal={setInterviewGoal} resumeFile={resumeFile} setResumeFile={setResumeFile}
               contextText={contextText} setContextText={setContextText}
               onStart={() => setScreen('live')} onBack={() => setScreen('landing')} onPractice={() => setScreen('practice')} />
      )}

      {screen === 'live' && (
        <LiveInterview apiBase={API_BASE_URL} goal={interviewGoal} contextText={contextText} resumeFile={resumeFile}
                       onBack={() => setScreen('setup')} onFinish={startReport} />
      )}

      {screen === 'report' && session && (
        <SessionReport report={session.report} audioURL={session.audioURL} progress={session.progress}
                       streaming={session.streaming} error={session.error}
                       onRetry={() => startReport(run.current.form, run.current.audioURL)}
                       onRestart={() => { run.current.id++; setSession(null); setScreen('setup'); }}
                       onHome={() => { run.current.id++; setSession(null); setScreen('landing'); }} />
      )}

      {screen === 'practice' && (
        <QuickPractice apiBase={API_BASE_URL} goal={interviewGoal} contextText={contextText}
                       resumeFile={resumeFile} onHome={() => setScreen('landing')} onLive={() => setScreen('setup')} />
      )}
    </div>
  );
}

export default App;
