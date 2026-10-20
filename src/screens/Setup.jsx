import React, { useEffect, useRef, useState } from 'react';
import { TopBar } from './Landing';
import './screens.css';

const TRACKS = [
  { value: 'academic', label: 'Academic', desc: 'College, scholarship and grad school interviews.',
    icon: 'M2.5 9 12 4.5 21.5 9 12 13.5zM6.5 11v4.5c1.5 1.5 3.4 2.2 5.5 2.2s4-.7 5.5-2.2V11M21.5 9v5' },
  { value: 'career', label: 'Career', desc: 'Internships and jobs. Behavioral and resume questions.',
    icon: 'M3 9a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM9 7V5.5A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5V7M3 12.5h18' },
  { value: 'social', label: 'Social', desc: 'Clubs, student orgs and volunteer roles.',
    icon: 'M4 5h11a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H9l-4 3v-3H4a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2zM19.5 9H20a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-1v2.5L16 18h-4' },
];

// The backend only extracts text from PDFs (PyPDF2), so only accept PDFs here.
const isPdf = (f) => f && /\.pdf$/i.test(f.name);

// One screen before the interview: resume, job description, track, device check.
// Resume and job description are both required: the interviewer's questions come from the resume and are
// aimed at the posting, so an interview without either is a generic one. Copy follows
// docs/product-polish/spec.md section 2.2.
export default function Setup({ apiBase, goal, setGoal, resumeFile, setResumeFile,
                                contextText, setContextText, jobUrl, setJobUrl, onStart, onBack, onPractice }) {
  const pick = (f) => isPdf(f) && setResumeFile(f);
  const missing = [!resumeFile && 'your resume', !contextText.trim() && 'the job description', !goal && 'a track']
    .filter(Boolean);

  return (
    <div className="screen-page">
      <TopBar onHome={onBack} />
      <main className="setup">
        <div className="setup-title">
          <h1 className="display">Set up your session</h1>
          <p>Takes under a minute. Nothing is recorded until you start.</p>
        </div>

        <section className="field">
          <div className="field-head">
            <h2>Resume <small>Required</small></h2>
          </div>
          {resumeFile ? (
            <div className="drop is-done">
              <FileIcon />
              <p><b>{resumeFile.name}</b><small>Ready. The interviewer will ask about it.</small></p>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => setResumeFile(null)}>Remove</button>
            </div>
          ) : (
            <label className="drop" onDragOver={(e) => e.preventDefault()}
                   onDrop={(e) => { e.preventDefault(); pick(e.dataTransfer.files[0]); }}>
              <FileIcon />
              <p><b>Drop your resume here</b> or <u>browse</u><small>PDF only. The interviewer uses it to pick questions.</small></p>
              <input type="file" accept=".pdf,application/pdf" className="visually-hidden" onChange={(e) => pick(e.target.files[0])} />
            </label>
          )}
        </section>

        <section className="field">
          <div className="field-head"><h2>Job description <small>Required</small></h2></div>
          <JobDescription apiBase={apiBase} text={contextText} setText={setContextText}
                          url={jobUrl} setUrl={setJobUrl} />
        </section>

        <fieldset className="field">
          <div className="field-head"><h2>Track</h2></div>
          <div className="tracks">
            {TRACKS.map((t) => (
              <label key={t.value} className="track">
                <input type="radio" name="track" value={t.value} checked={goal === t.value} onChange={() => setGoal(t.value)} />
                <span className="check"><svg viewBox="0 0 12 12"><path d="m2.5 6.2 2.3 2.3 4.7-5" /></svg></span>
                <svg className="icon" viewBox="0 0 24 24" aria-hidden="true"><path d={t.icon} /></svg>
                <b>{t.label}</b>
                <span>{t.desc}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <section className="field">
          <div className="field-head"><h2>Mic and camera</h2></div>
          <DeviceCheck onPractice={onPractice} />
        </section>

        <div className="setup-foot">
          <p>{missing.length ? `Still needed: ${missing.join(', ')}.`
                             : 'About 3 questions with follow-ups, 5 to 8 minutes. You can end it any time.'}</p>
          <div>
            <button type="button" className="btn btn-secondary" onClick={onBack}>Back</button>
            <button type="button" className="btn btn-lg" disabled={missing.length > 0} onClick={onStart}>Start interview</button>
          </div>
        </div>
      </main>
    </div>
  );
}

// Two ways to give the interviewer the posting: paste a link and let the backend read it, or paste the text.
// The fetched text lands in the same box, so the user can see and edit exactly what the interviewer gets.
// Link reading is best effort. Boards that need a login (LinkedIn often does) answer with a login wall, and
// the backend says so instead of sending an empty page to the interviewer.
function JobDescription({ apiBase, text, setText, url, setUrl }) {
  const [state, setState] = useState('idle'); // idle | reading | read | error
  const [note, setNote] = useState('');

  async function read() {
    if (!url.trim() || state === 'reading') return;
    setState('reading');
    setNote('');
    try {
      const fd = new FormData();
      fd.append('url', url.trim());
      const res = await fetch(`${apiBase}/api/job_post`, { method: 'POST', body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || `We could not read that link (${res.status}).`);
      setText(data.text);
      setState('read');
      setNote(`Read ${data.chars.toLocaleString()} characters from ${hostOf(data.url)}. Check it below, and edit it if the page picked up extra text.`);
    } catch (e) {
      setState('error');
      // "Failed to fetch" means the backend is not reachable, not that the link is bad.
      setNote(e instanceof TypeError ? "Can't reach the backend. Start it with `npm start`, then try again." : e.message);
    }
  }

  return (
    <div className="jd">
      <div className="jd-url">
        <input type="url" inputMode="url" value={url} aria-label="Link to the job posting"
               placeholder="Paste a link to the posting, including LinkedIn"
               onChange={(e) => { setUrl(e.target.value); setState('idle'); setNote(''); }}
               onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); read(); } }} />
        <button type="button" className="btn btn-secondary" disabled={!url.trim() || state === 'reading'} onClick={read}>
          {state === 'reading' ? 'Reading' : 'Read link'}
        </button>
      </div>
      {note && <p className={state === 'error' ? 'jd-note is-error' : 'jd-note is-ok'}>{note}</p>}
      <label className="jd-text">
        <span>{state === 'read' ? 'What the interviewer will read' : 'Or paste the job description'}</span>
        <textarea rows="7" value={text} onChange={(e) => setText(e.target.value)}
                  placeholder="Paste the responsibilities and requirements. The interviewer aims its questions at this." />
      </label>
      <p className="hint">{text.trim()
        ? `${text.trim().length.toLocaleString()} characters. ${text.trim().length < 200 ? 'Short descriptions give more generic questions.' : 'Long enough for targeted questions.'}`
        : 'Needed so the interviewer asks about this role instead of asking generic questions.'}</p>
    </div>
  );
}

const hostOf = (u) => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return 'that page'; } };

const FileIcon = () => (
  <svg className="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5M12 17v-6M9.5 13.5 12 11l2.5 2.5" /></svg>
);

// Asks for mic + camera, shows a live mic level and a camera preview. Everything is released when the screen
// unmounts so LiveInterview can open the devices itself.
function DeviceCheck({ onPractice }) {
  const [state, setState] = useState('idle'); // idle | checking | ready | blocked | nomic
  const [level, setLevel] = useState(0);
  const [camera, setCamera] = useState(false);
  const videoRef = useRef(null);
  const dev = useRef({});
  const alive = useRef(true);

  const stop = () => {
    const d = dev.current;
    cancelAnimationFrame(d.raf);
    d.stream?.getTracks().forEach((t) => t.stop());
    d.ctx?.close();
    dev.current = {};
  };
  useEffect(() => { alive.current = true; return () => { alive.current = false; stop(); }; }, []);

  async function check() {
    stop();
    setState('checking');
    let stream;
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true }); }
    catch {
      try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
      catch (e) { setState(e.name === 'NotFoundError' ? 'nomic' : 'blocked'); return; }
    }
    if (!alive.current) { stream.getTracks().forEach((t) => t.stop()); return; } // left the screen while the prompt was open

    const ctx = new AudioContext();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 512;
    ctx.createMediaStreamSource(stream).connect(analyser);
    const buf = new Uint8Array(analyser.fftSize);
    const d = dev.current = { stream, ctx };
    const tick = () => {
      analyser.getByteTimeDomainData(buf);
      let peak = 0;
      for (const v of buf) peak = Math.max(peak, Math.abs(v - 128));
      setLevel(peak / 128);
      d.raf = requestAnimationFrame(tick);
    };
    tick();

    const hasCam = stream.getVideoTracks().length > 0;
    setCamera(hasCam);
    if (hasCam) { videoRef.current.srcObject = stream; videoRef.current.play().catch(() => {}); }
    setState('ready');
  }

  const bars = 20, on = Math.round(Math.min(level * 3, 1) * bars);
  return (
    <div className="devices">
      <div className="cam">
        <video ref={videoRef} muted playsInline hidden={!camera} />
        {!camera && <span className="cam-empty">{state === 'ready' ? 'Camera off' : 'Camera preview'}</span>}
        {camera && <span className="status-ok cam-status"><span className="dot" />Camera on</span>}
      </div>
      <div className="mic">
        {state !== 'ready' && (
          <button type="button" className="btn btn-secondary" onClick={check} disabled={state === 'checking'}>
            {state === 'checking' ? 'Waiting for permission' : state === 'idle' ? 'Check mic and camera' : 'Try again'}
          </button>
        )}
        {state === 'ready' && (
          <>
            <span className="label">Microphone</span>
            <div className="meter" role="meter" aria-label="Microphone level" aria-valuemin="0" aria-valuemax="1" aria-valuenow={level.toFixed(2)}>
              {Array.from({ length: bars }, (_, k) => <i key={k} className={k < on ? (k >= bars - 3 ? 'on hot' : 'on') : ''} />)}
            </div>
            <p className="hint">{level < 0.05 ? 'Say a few words. The bar should move.' : <span className="status-ok"><span className="dot" />Mic is working</span>}</p>
            {!camera && <p className="hint">Camera is off. You can still do the interview; eye contact won't be measured.</p>}
          </>
        )}
        {state === 'blocked' && <p className="hint">Your microphone is blocked. Click the lock icon in the address bar, allow Microphone, then try again.{' '}
          <button type="button" className="link-btn" onClick={onPractice}>Practice by typing instead</button></p>}
        {state === 'nomic' && <p className="hint">We can't find a microphone. Plug one in or check your system settings.</p>}
        <p className="hint">Use headphones if you can, so the interviewer's voice doesn't reach your mic. Video stays on this device.</p>
      </div>
    </div>
  );
}
