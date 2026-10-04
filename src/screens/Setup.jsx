import React, { useEffect, useRef, useState } from 'react';

const TRACKS = [
  { value: 'academic', label: 'Academic', desc: 'College, scholarship and grad school interviews' },
  { value: 'career', label: 'Career', desc: 'Internships and job interviews' },
  { value: 'social', label: 'Social', desc: 'Clubs, student orgs and volunteer roles' },
];

// The backend only extracts text from PDFs (PyPDF2), so only accept PDFs here.
const isPdf = (f) => f && /\.pdf$/i.test(f.name);

// One screen before the interview: resume (optional), track, device check, and extra options folded away.
// Copy follows docs/product-polish/spec.md section 2.2.
export default function Setup({ goal, setGoal, resumeFile, setResumeFile,
                                contextText, setContextText, onStart, onBack, onPractice }) {
  const [skipped, setSkipped] = useState(false);

  return (
    <main className="app-container setup">
      <header className="app-header">
        <h1>Set up your interview</h1>
        <p className="subtitle">Takes about 30 seconds.</p>
      </header>

      <section className="setup-section">
        <h3>Resume <span className="setup-optional">(optional)</span></h3>
        {resumeFile ? (
          <p>{resumeFile.name} · Ready <button type="button" className="link-btn" onClick={() => setResumeFile(null)}>Remove</button></p>
        ) : skipped ? (
          <p>No resume. You'll get general questions for the type you pick.{' '}
            <button type="button" className="link-btn" onClick={() => setSkipped(false)}>Add resume</button></p>
        ) : (
          <>
            <input type="file" accept=".pdf" id="resume-upload" className="file-input"
                   onChange={(e) => isPdf(e.target.files[0]) && setResumeFile(e.target.files[0])} />
            <label htmlFor="resume-upload" className="upload-label"
                   onDragOver={(e) => e.preventDefault()}
                   onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (isPdf(f)) setResumeFile(f); }}>
              <span className="upload-text">Drop your resume here or browse</span>
              <span className="upload-hint">PDF</span>
            </label>
            <p className="camera-note">No resume?{' '}
              <button type="button" className="link-btn" onClick={() => setSkipped(true)}>Skip</button>
              {' '}this. You'll get general questions for the type you pick.</p>
          </>
        )}
      </section>

      <section className="setup-section">
        <h3>Interview type</h3>
        <div className="age-cards" role="radiogroup" aria-label="Interview type">
          {TRACKS.map((t) => (
            <button key={t.value} type="button" role="radio" aria-checked={goal === t.value}
                    className={`age-card ${goal === t.value ? 'selected' : ''}`} onClick={() => setGoal(t.value)}>
              <span className="age-label">{t.label}</span>
              <span className="age-desc">{t.desc}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="setup-section">
        <h3>Mic and camera</h3>
        <DeviceCheck onPractice={onPractice} />
      </section>

      <details className="setup-section">
        <summary>More options</summary>
        <label className="setup-field">Job description or notes
          <textarea className="context-textarea" rows="4" value={contextText} onChange={(e) => setContextText(e.target.value)}
                    placeholder="Paste a job description, the role you're applying for, or questions you want to practice." />
        </label>
      </details>

      <p className="camera-note">About 3 questions with follow-ups. 5 to 8 minutes.</p>
      <div className="step-buttons">
        <button type="button" className="btn btn-secondary" onClick={onBack}>Back</button>
        <button type="button" className="btn btn-submit" disabled={!goal} onClick={onStart}>Start interview</button>
      </div>
      {!goal && <p className="camera-note">Pick an interview type to start.</p>}
    </main>
  );
}

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

  return (
    <div className="camera-panel">
      {state !== 'ready' && (
        <button type="button" className="btn btn-secondary" onClick={check} disabled={state === 'checking'}>
          {state === 'checking' ? 'Waiting for permission' : state === 'idle' ? 'Check mic and camera' : 'Try again'}
        </button>
      )}
      {state === 'blocked' && <p className="camera-note">Your microphone is blocked. The interviewer needs to hear you.
        Click the lock icon in the address bar, allow Microphone, then try again.{' '}
        <button type="button" className="link-btn" onClick={onPractice}>Practice by typing instead</button></p>}
      {state === 'nomic' && <p className="camera-note">We can't find a microphone. Plug one in or check your system settings.</p>}
      {state === 'ready' && (
        <label>Mic level <meter min="0" max="1" low="0.05" value={level} aria-label="Microphone level" /></label>
      )}
      {state === 'ready' && <p className="camera-note">{level < 0.05 ? 'Say something. The bar should move.' : 'Mic is working'}</p>}
      <video ref={videoRef} className="camera-preview" muted playsInline hidden={!camera} />
      {state === 'ready' && !camera && <p className="camera-note">Camera is off. You can still do the interview. Eye contact won't be measured.</p>}
      {camera && <p className="camera-note">Camera is on. It only measures where you look, on this device.</p>}
    </div>
  );
}
