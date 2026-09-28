import React, { useEffect, useRef, useState } from 'react';
import { startLiveSession } from '../live/liveSession';
import { createFaceSignalTracker } from '../signals/faceSignals';
import { aggregateSignals } from '../signals/aggregate';

// A spoken mock interview with Gemini Live. The interviewer's questions come from the resume; the candidate's mic is
// also recorded locally so the whole session can be scored afterwards. Video never leaves the device.
export default function LiveInterview({ apiBase, goal, contextText, resumeFile, onReport, onBack }) {
  const [status, setStatus] = useState('idle'); // idle | connecting | live | scoring | error
  const [note, setNote] = useState('');
  const [captions, setCaptions] = useState([]);
  const [cameraOn, setCameraOn] = useState(true);
  const [elapsed, setElapsed] = useState(0);
  const videoRef = useRef(null);
  const captionsRef = useRef(null);
  const live = useRef({});

  useEffect(() => { captionsRef.current?.scrollTo(0, captionsRef.current.scrollHeight); }, [captions]);
  useEffect(() => () => cleanup(), []); // leaving the page mid-interview releases mic and camera

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
    setStatus('connecting'); setNote(''); setCaptions([]); setElapsed(0);
    try {
      const res = await fetch(`${apiBase}/api/live/token`, { method: 'POST', body: form() });
      const { token, model, error } = await res.json();
      if (!res.ok) throw new Error(error || `Token request failed (${res.status})`);

      let stream;
      const audio = { echoCancellation: true, noiseSuppression: true };
      try { stream = await navigator.mediaDevices.getUserMedia({ audio, video: cameraOn }); }
      catch { stream = await navigator.mediaDevices.getUserMedia({ audio }); setCameraOn(false); }
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
      setStatus('live');
      l.timer = setInterval(() => setElapsed(Math.round(l.session.clock())), 1000);
    } catch (e) {
      cleanup();
      setStatus('error');
      // "Failed to fetch" means the backend isn't running, which is the usual local setup mistake.
      setNote(e instanceof TypeError ? 'Can\'t reach the backend. Start it with `npm start` (or `./.venv/bin/python backend.py`), then try again.' : e.message);
    }
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

  const running = status === 'live' || status === 'connecting';
  const mm = `${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, '0')}`;
  return (
    <div className="live-interview">
      <div className="live-bar">
        <span className="live-status" data-state={status === 'idle' ? 'connecting' : status}>
          {{ idle: 'Ready', connecting: 'Connecting…', live: 'Interview in progress', scoring: 'Preparing your report…', error: 'Something went wrong' }[status]}
        </span>
        {status === 'live' && <span className="live-timer">{mm}</span>}
      </div>

      <div className="live-stage">
        <div className="live-camera">
          <label>
            <input type="checkbox" checked={cameraOn} disabled={running}
                   onChange={(e) => setCameraOn(e.target.checked)} /> Use camera for eye contact &amp; presence
          </label>
          <video ref={videoRef} className="camera-preview" muted playsInline hidden={!cameraOn || status === 'idle'} />
          <p className="camera-note">Video is analysed on your device and never uploaded. Headphones stop the interviewer hearing itself.</p>
        </div>
        <div className="captions" ref={captionsRef} aria-live="polite">
          {captions.length === 0 && <p className="captions-empty">
            {status === 'idle' ? 'The interviewer will ask about your resume and follow up on what you say.' : 'Listening…'}</p>}
          {captions.map((c, i) => (
            <p key={i} className={`caption ${c.role}`}>
              <span className="caption-role">{c.role === 'interviewer' ? 'Interviewer' : 'You'}</span>{c.text}
            </p>
          ))}
        </div>
      </div>

      {note && <p className="live-hint">{note}</p>}
      <div className="live-actions">
        {status === 'idle' || (status === 'error' && !live.current.retry)
          ? <>
              <button type="button" className="btn btn-secondary" onClick={onBack}>← Back</button>
              <button type="button" className="btn-end" onClick={start}>🎙️ Start interview</button>
            </>
          : <button type="button" className="btn-end" disabled={status === 'scoring' || status === 'connecting'} onClick={finish}>
              {status === 'scoring' ? 'Scoring…' : 'End & get report'}
            </button>}
      </div>
      <p className="live-hint">About 3 questions with follow-ups, 5–8 minutes. You can interrupt the interviewer any time.</p>
    </div>
  );
}
