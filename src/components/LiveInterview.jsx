import React, { useEffect, useRef, useState } from 'react';
import { startLiveSession } from '../live/liveSession';
import { createFaceSignalTracker } from '../signals/faceSignals';
import { aggregateSignals } from '../signals/aggregate';
import '../screens/session.css';

// A spoken mock interview with Gemini Live. The interviewer's questions come from the resume; the candidate's mic is
// also recorded locally so the whole session can be scored afterwards. Video never leaves the device.
export default function LiveInterview({ apiBase, goal, contextText, resumeFile, onReport, onBack }) {
  const [status, setStatus] = useState('idle'); // idle | connecting | live | scoring | error
  const [note, setNote] = useState('');
  const [captions, setCaptions] = useState([]);
  const [cameraOn, setCameraOn] = useState(true);
  const [elapsed, setElapsed] = useState(0);
  const [muted, setMuted] = useState(false);
  const videoRef = useRef(null);
  const captionsRef = useRef(null);
  const live = useRef({});
  const alive = useRef(true);
  const started = useRef(false);

  useEffect(() => { captionsRef.current?.scrollTo(0, captionsRef.current.scrollHeight); }, [captions]);
  // Leaving the page mid-interview releases mic and camera. `alive` also stops a start() that is still waiting on a permission prompt.
  useEffect(() => { alive.current = true; return () => { alive.current = false; cleanup(); }; }, []);
  // The interview begins as soon as this screen opens (Setup's button was the start). The ref keeps StrictMode's dev double-mount from starting twice.
  useEffect(() => { if (!started.current) { started.current = true; start(); } }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const form = () => {
    const fd = new FormData();
    fd.append('goal', goal || 'career');
    fd.append('context_text', contextText || '');
    if (resumeFile) fd.append('file', resumeFile);
    return fd;
  };

  function cleanup() {
    const l = live.current;
    clearInterval(l.timer);
    const turns = l.session?.stop() || [];
    const samples = l.tracker?.stop() || [];
    if (l.recorder?.state === 'recording') l.recorder.stop();
    l.stream?.getTracks().forEach((t) => t.stop());
    live.current = {};
    return { turns, samples, recorder: l.recorder, chunks: l.chunks, stopped: l.stopped };
  }

  async function start() {
    setStatus('connecting'); setNote(''); setCaptions([]); setElapsed(0); setMuted(false);
    try {
      const res = await fetch(`${apiBase}/api/live/token`, { method: 'POST', body: form() });
      const { token, model, error } = await res.json();
      if (!res.ok) throw new Error(error || `Token request failed (${res.status})`);
      if (!alive.current) return;

      let stream;
      const audio = { echoCancellation: true, noiseSuppression: true };
      try { stream = await navigator.mediaDevices.getUserMedia({ audio, video: cameraOn }); }
      catch { stream = await navigator.mediaDevices.getUserMedia({ audio }); setCameraOn(false); }
      if (!alive.current) { stream.getTracks().forEach((t) => t.stop()); return; }
      const l = live.current = { stream, chunks: [] };

      if (stream.getVideoTracks().length && videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
        l.tracker = await createFaceSignalTracker(videoRef.current);
        l.tracker?.start();
      }
      // The recording and the live session share one clock, so feedback timestamps match the playback.
      l.recorder = new MediaRecorder(new MediaStream(stream.getAudioTracks()));
      l.recorder.ondataavailable = (e) => e.data.size && l.chunks.push(e.data);
      l.stopped = new Promise((r) => { l.recorder.onstop = r; }); // the last chunk arrives after stop(), before onstop
      l.recorder.start(1000);
      l.session = await startLiveSession({
        token, model, stream,
        onCaptions: setCaptions,
        onStatus: (s, detail) => { if (s === 'error') { setStatus('error'); setNote(detail); } else if (detail) setNote(detail); },
        onInterviewDone: () => finish(),
      });
      if (!alive.current) { cleanup(); return; }
      setStatus('live'); setMuted(false);
      l.timer = setInterval(() => setElapsed(Math.round(l.session.clock())), 1000);
    } catch (e) {
      cleanup();
      setStatus('error');
      // "Failed to fetch" means the backend isn't running, which is the usual local setup mistake.
      setNote(e instanceof TypeError ? 'Can\'t reach the backend. Start it with `npm start` (or `./.venv/bin/python backend.py`), then try again.' : e.message);
    }
  }

  function toggleMute() {
    const next = !muted;
    live.current.stream?.getAudioTracks().forEach((t) => { t.enabled = !next; });
    setMuted(next);
  }

  async function finish() {
    if (!live.current.session) return;
    setStatus('scoring');
    const { turns, samples, recorder, chunks, stopped } = cleanup();
    await stopped;
    const type = recorder.mimeType || 'audio/webm';
    const blob = new Blob(chunks, { type });
    const fd = form();
    fd.append('audio_response', blob, `session.${type.includes('mp4') ? 'm4a' : 'webm'}`);
    fd.append('turns', JSON.stringify(turns));
    if (samples.length) fd.append('video_signals', JSON.stringify(aggregateSignals(samples)));
    try {
      const res = await fetch(`${apiBase}/api/session_report`, { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `Report failed (${res.status})`);
      onReport(data, URL.createObjectURL(blob));
    } catch (e) {
      setStatus('error');
      setNote(`${e.message} Your answers were not lost from this page: try "End & get report" again.`);
      live.current = { session: { stop: () => turns }, recorder, chunks, stopped: Promise.resolve(), retry: true };
    }
  }

  const mm = `${String(Math.floor(elapsed / 60)).padStart(2, '0')}:${String(elapsed % 60).padStart(2, '0')}`;
  const lastCaption = captions[captions.length - 1];
  const lastInterviewer = [...captions].reverse().find((c) => c.role === 'interviewer');
  // State shown on the stage: what the interviewer is doing right now.
  const state = status === 'connecting' || status === 'idle' ? 'connecting'
    : status === 'scoring' ? 'thinking'
    : lastCaption?.role === 'interviewer' ? 'speaking' : 'listening';
  const stateLabel = { connecting: 'Connecting…', speaking: 'Speaking', listening: 'Listening', thinking: 'Preparing your report' }[state];
  const failed = status === 'error';

  return (
    <div className="call" data-state={state} data-muted={muted}>
      <div className="call-top">
        <span className="call-title"><span className="dot" />{goal ? `${goal[0].toUpperCase()}${goal.slice(1)} mock interview` : 'Mock interview'}</span>
        <span className="call-timer mono">{mm}<small> of about 10:00</small></span>
      </div>

      <div className="call-stage">
        <div className="presence"><span className="ring" /><span className="face">
          <svg viewBox="0 0 40 40" aria-hidden="true"><path d="M8 20h3M15 13v14M20 8v24M25 14v12M30 18v4" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" fill="none" /></svg>
        </span></div>
        <span className="state-pill" aria-live="polite">
          <span className={`viz viz-${state}`} aria-hidden="true"><i /><i /><i /><i /><i /></span>
          {stateLabel}
        </span>

        {failed ? (
          <div className="call-question">
            <span className="label">Something went wrong</span>
            <p className="q display">{note || 'The connection was interrupted.'}</p>
          </div>
        ) : state === 'connecting' ? (
          <div className="call-question">
            <span className="label">Connecting to your interviewer</span>
            <p className="q display">Allow the microphone if your browser asks.</p>
            <p className="sub">The first question usually arrives within a few seconds. Headphones stop the interviewer hearing itself.</p>
          </div>
        ) : state === 'thinking' ? (
          <div className="call-question">
            <span className="label">Interview finished</span>
            <p className="q display">Building your report. This takes about a minute.</p>
          </div>
        ) : (
          <div className="call-question">
            <span className="label">{lastInterviewer ? 'Interviewer' : 'Get ready'}</span>
            <p className="q display">{lastInterviewer ? lastInterviewer.text : 'The interviewer will start with a question about you.'}</p>
          </div>
        )}

        <div className="self" aria-label="Your camera">
          <video ref={videoRef} className="self-video" muted playsInline hidden={!cameraOn || status !== 'live'} />
          {(!cameraOn || status !== 'live') && <svg className="self-person" viewBox="0 0 100 90" aria-hidden="true"><circle cx="50" cy="30" r="20" /><path d="M8 90c2-22 20-34 42-34s40 12 42 34z" /></svg>}
          <span className="self-tag">{muted ? 'You (muted)' : 'You'}</span>
        </div>
      </div>

      {captions.length > 0 && (
        <details className="call-transcript">
          <summary>Live transcript</summary>
          <div className="captions" ref={captionsRef} aria-live="polite">
            {captions.map((c, i) => (
              <p key={i} className={`caption ${c.role}`}><span className="caption-role">{c.role === 'interviewer' ? 'Interviewer' : 'You'}</span>{c.text}</p>
            ))}
          </div>
        </details>
      )}

      <div className="controls">
        {failed && !live.current.retry ? (
          <>
            <button type="button" className="call-btn" onClick={onBack}>Back</button>
            <button type="button" className="call-btn call-btn-solid" onClick={start}>Try again</button>
          </>
        ) : (
          <>
            <div className="ctrl">
              <button type="button" className="round" aria-pressed={muted} aria-label={muted ? 'Unmute' : 'Mute'}
                      disabled={status !== 'live'} onClick={toggleMute}>
                <svg className="icon" viewBox="0 0 24 24" aria-hidden="true">
                  <rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" />
                  {muted && <path d="M4 4l16 16" />}
                </svg>
              </button>
              <span className="ctrl-label">{muted ? 'Unmute' : 'Mute'}</span>
            </div>
            <div className="ctrl">
              <button type="button" className="end" disabled={status === 'scoring' || status === 'connecting'} onClick={finish}>
                {status === 'scoring' ? 'Scoring…' : 'End interview'}
              </button>
              <span className="ctrl-label">Your report is ready in about a minute</span>
            </div>
          </>
        )}
      </div>
      {!failed && note && <p className="call-note">{note}</p>}
    </div>
  );
}
