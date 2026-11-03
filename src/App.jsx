import React, { useEffect, useRef, useState } from 'react';
import './App.css';
import LiveInterview from './components/LiveInterview';
import SessionReport from './components/SessionReport';
import Landing from './screens/Landing';
import Setup from './screens/Setup';
import QuickPractice from './screens/QuickPractice';
import AuthScreen from './components/AuthScreen';
import { apiFetch, getToken, setToken, track, LOGIN_EVENT } from './api';
import { countWords, MIN_JD_WORDS } from './jobWords';

const API_BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:5002';

// Main path: landing -> setup -> live -> report. Quick Practice ('practice') is reached from the landing link; it asks for the
// same resume and job description first, so it goes through Setup when they are not filled in yet.
function App() {
  // #setup opens Setup directly (handy for screenshots and sharing); every other screen needs state from earlier ones.
  const planParam = new URLSearchParams(window.location.search).get('plan');
  const [screen, setScreen] = useState(() => (window.location.hash === '#setup' || planParam ? 'setup' : 'landing')); // landing | setup | live | report | practice
  // A practice opened from a calendar invite: its first question is aimed at the weak spot from the last report.
  const [plan, setPlan] = useState(null);
  useEffect(() => {
    if (!planParam) return;
    apiFetch(API_BASE_URL, `/api/plan/${encodeURIComponent(planParam)}`).then((r) => (r.ok ? r.json() : null))
      .then((p) => { if (p) { setPlan(p); track(API_BASE_URL, 'plan_opened', { focus: p.label }); } }).catch(() => {});
  }, [planParam]);

  // Shared inputs: Setup fills them, the live interview and Quick Practice send them to the backend.
  const [interviewGoal, setInterviewGoal] = useState('');
  const [resumeFile, setResumeFile] = useState(null);
  const [ageGroup, setAgeGroup] = useState('');
  const [setupMode, setSetupMode] = useState('live'); // what Setup's button starts: the live interview or one practice question
  const [contextText, setContextText] = useState('');
  const [jobUrl, setJobUrl] = useState(''); // kept here so going Back from the interview does not lose the link

  // Signed-in account (its email) and the sign-in dialog, which opens when the backend says the free practice is used up.
  const [user, setUser] = useState(null);
  const [auth, setAuth] = useState(null); // null | { message }
  useEffect(() => {
    if (getToken()) {
      apiFetch(API_BASE_URL, '/api/auth/me').then((r) => (r.ok ? r.json() : null))
        .then((d) => { if (d?.email) setUser(d.email); else setToken(null); }).catch(() => {});
    }
    const onLogin = (e) => {
      setToken(null); setUser(null);
      setAuth({ message: e.detail });
      track(API_BASE_URL, 'login_prompted', {});
    };
    window.addEventListener(LOGIN_EVENT, onLogin);
    return () => window.removeEventListener(LOGIN_EVENT, onLogin);
  }, []);
  useEffect(() => { if (screen === 'landing') track(API_BASE_URL, 'home_view', {}, { once: true }); }, [screen]);

  const openSetup = (mode) => { setSetupMode(mode); setScreen('setup'); };
  // One-question practice needs the same inputs as the interview. With them filled in, go straight there.
  const inputsReady = resumeFile && interviewGoal && countWords(contextText) >= MIN_JD_WORDS;
  const openPractice = () => (inputsReady ? setScreen('practice') : openSetup('practice'));

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
      else if (ev.type === 'done') { update((s) => ({ ...s, report: ev.report, streaming: false })); track(API_BASE_URL, 'report_viewed', { kind: 'live' }); }
      else if (ev.type === 'error') throw new Error(ev.error);
    };
    try {
      const res = await apiFetch(API_BASE_URL, '/api/session_report/stream', { method: 'POST', body: fd });
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
      {screen === 'landing' && <Landing onStart={() => openSetup('live')} onPractice={openPractice} />}

      {screen === 'setup' && (
        <Setup apiBase={API_BASE_URL} mode={setupMode} goal={interviewGoal} setGoal={setInterviewGoal}
               resumeFile={resumeFile} setResumeFile={setResumeFile} ageGroup={ageGroup} setAgeGroup={setAgeGroup}
               contextText={contextText} setContextText={setContextText} jobUrl={jobUrl} setJobUrl={setJobUrl} plan={plan}
               onStart={() => setScreen(setupMode === 'practice' ? 'practice' : 'live')} onBack={() => setScreen('landing')}
               onPractice={() => (inputsReady ? setScreen('practice') : setSetupMode('practice'))} />
      )}

      {screen === 'live' && (
        <LiveInterview apiBase={API_BASE_URL} goal={interviewGoal} contextText={contextText} resumeFile={resumeFile} ageGroup={ageGroup} planId={plan?.plan_id}
                       onBack={() => setScreen('setup')} onFinish={startReport} />
      )}

      {screen === 'report' && session && (
        <SessionReport report={session.report} audioURL={session.audioURL} progress={session.progress}
                       streaming={session.streaming} error={session.error}
                       apiBase={API_BASE_URL} signedIn={!!user} onSignIn={() => setAuth({ message: null })}
                       onRetry={() => startReport(run.current.form, run.current.audioURL)}
                       onRestart={() => { run.current.id++; setSession(null); setScreen('setup'); }}
                       onHome={() => { run.current.id++; setSession(null); setScreen('landing'); }} />
      )}

      {screen === 'practice' && (
        <QuickPractice apiBase={API_BASE_URL} goal={interviewGoal} contextText={contextText} ageGroup={ageGroup}
                       resumeFile={resumeFile} planId={plan?.plan_id} onHome={() => setScreen('landing')} onLive={() => openSetup('live')} />
      )}

      {auth && (
        <AuthScreen apiBase={API_BASE_URL} message={auth.message} onClose={() => setAuth(null)}
                    onDone={(email, how) => { setUser(email); setAuth(null); if (how === 'signup') track(API_BASE_URL, 'account_created', {}); }} />
      )}
    </div>
  );
}

export default App;
