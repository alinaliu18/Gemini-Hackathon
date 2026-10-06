import React, { useEffect, useRef, useState } from 'react';
import EvidenceFeedback from './EvidenceFeedback';
import { TopBar } from '../screens/Landing';
import '../screens/session.css';

const secs = (mmss) => { const [m, s] = String(mmss).split(':').map(Number); return m * 60 + s; };
const mmss = (t) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
const firstT = (item) => { const t = item?.evidence?.[0]?.t; return t != null && !Number.isNaN(secs(t)) ? secs(t) : null; };

// Report for a whole live interview, read like a document: header, a timeline of the session,
// the three things to work on first, then each question with its own feedback.
// Every timestamp (chip or timeline marker) jumps the recording to that moment.
function Steps({ progress, report, streaming }) {
  const { done, total } = progress;
  const ready = report.answers.length;
  const items = [
    { label: 'Transcribing your answers', detail: total ? `${done} of ${total}` : '', state: total && done >= total ? 'done' : 'active' },
    { label: 'Writing feedback for each answer', detail: total ? `${ready} of ${total}` : '', state: total && ready >= total ? 'done' : done > 0 ? 'active' : 'wait' },
    { label: 'Summing up the whole interview', detail: '', state: report.summary ? 'done' : done >= total && total > 0 ? 'active' : 'wait' },
  ];
  return (
    <ol className="steps-live" aria-live="polite" aria-label="Report progress">
      {items.map((it) => (
        <li key={it.label} className={`step-${it.state}`}>
          <span className="step-mark" aria-hidden="true">{it.state === 'done' ? '✓' : ''}</span>
          <span>{it.label}</span><span className="mono step-detail">{it.detail}</span>
        </li>
      ))}
      {streaming && <li className="steps-hint">You can read each part as soon as it appears.</li>}
    </ol>
  );
}

export default function SessionReport({ report, audioURL, progress = { done: 0, total: 0 }, streaming = false, error = null, onRetry, onRestart, onHome }) {
  const player = useRef(null);
  const [now, setNow] = useState(0);
  const [duration, setDuration] = useState(0);
  const [open, setOpen] = useState(0);
  const s = report.summary;
  const answers = report.answers || [];
  const pending = Math.max(0, (progress.total || 0) - answers.length);

  useEffect(() => {
    const a = player.current; if (!a) return undefined;
    const tick = () => setNow(a.currentTime || 0);
    const meta = () => setDuration(Number.isFinite(a.duration) ? a.duration : 0);
    a.addEventListener('timeupdate', tick); a.addEventListener('loadedmetadata', meta); a.addEventListener('durationchange', meta);
    return () => { a.removeEventListener('timeupdate', tick); a.removeEventListener('loadedmetadata', meta); a.removeEventListener('durationchange', meta); };
  }, [audioURL]);

  const seek = (t) => {
    const v = typeof t === 'number' ? t : secs(t);
    if (!player.current || Number.isNaN(v)) return;
    player.current.currentTime = v; setNow(v);
    player.current.play().catch(() => {});
  };

  const todo = (s?.improvements || []).slice(0, 3);
  const stamps = [...answers.map((a) => Number(a.asked_at) || 0), ...todo.map(firstT).filter((x) => x != null)];
  // Recorded blobs often report an unknown duration, so fall back to the last moment the report mentions.
  const total = duration || (stamps.length ? Math.max(...stamps) + 45 : 60);
  const pct = (t) => `${Math.min(100, (t / total) * 100)}%`;

  return (
    <div className="screen-page">
      <TopBar onHome={onHome} />
      <main className="report">
        <article className="doc">
          <header className="doc-head">
            <span className="label">{streaming ? 'Building your report' : 'Mock interview report'}</span>
            <h1 className="display">{streaming && !answers.length ? 'Reading your interview…' : `${answers.length} question${answers.length === 1 ? '' : 's'}, one conversation`}</h1>
            {(answers.length > 0 || !streaming) && (
              <div className="meta">
                <span><span className="k">Length</span><span className="mono">{mmss(total)}</span></span>
                <span><span className="k">Questions</span><span className="mono">{progress.total || answers.length}</span></span>
                {s?.score != null && <span><span className="k">Overall</span><span className="mono">{s.score} / 100</span></span>}
              </div>
            )}
          </header>

          {error && (
            <div className="report-error" role="alert">
              <p>{error}</p>
              {onRetry && <button type="button" className="btn" onClick={onRetry}>Try again</button>}
            </div>
          )}
          {(streaming || (error && !answers.length)) && !error && <Steps progress={progress} report={report} streaming={streaming} />}

          {audioURL && answers.length > 0 && (
            <div className="timeline" aria-label="Session timeline">
              <audio ref={player} src={audioURL} controls className="audio-player" />
              <div className="tl-track">
                {answers.map((a, i) => {
                  const start = Number(a.asked_at) || 0;
                  const end = answers[i + 1] ? Number(answers[i + 1].asked_at) || total : total;
                  return <span key={i} className="tl-seg" style={{ left: pct(start), width: `${Math.max(0, ((end - start) / total) * 100)}%` }}>{streaming ? '' : `Q${i + 1}`}</span>;
                })}
                {todo.map((item, i) => { const t = firstT(item); return t == null ? null : (
                  <button key={i} type="button" className="tl-num" style={{ left: pct(t) }} aria-label={`Item ${i + 1} at ${mmss(t)}`}
                          onClick={() => { setOpen(i); seek(t); }}>{i + 1}</button>
                ); })}
                <span className="tl-head" style={{ left: pct(now) }} />
              </div>
              <div className="tl-axis mono"><span>0:00</span><span>{mmss(total)}</span></div>
            </div>
          )}

          {!s && !streaming && !error ? <p className="coverage-note">{report.note || 'No answers were found in the recording.'}</p> : (
            <>
              {streaming && !s && answers.length > 0 && (
                <section className="sec" aria-busy="true">
                  <div className="sec-head"><h2 className="display">Top things to work on</h2><p>Writing…</p></div>
                  <div className="skeleton" /><div className="skeleton" />
                </section>
              )}
              {todo.length > 0 && (
                <section className="sec">
                  <div className="sec-head"><h2 className="display">{todo.length} thing{todo.length === 1 ? '' : 's'} to work on</h2><p>Most useful first</p></div>
                  <ol className="todo">
                    {todo.map((item, i) => (
                      <li key={i}>
                        <details open={open === i} onToggle={(e) => { if (e.currentTarget.open) setOpen(i); }}>
                          <summary>
                            <span className="n display">{i + 1}</span>
                            <h3>{item.text}</h3>
                            <span className="chips">
                              {(item.evidence || []).slice(0, 1).map((e, k) => <button key={k} type="button" className="evidence-time" onClick={(ev) => { ev.preventDefault(); seek(e.t); }}>{e.t}</button>)}
                            </span>
                          </summary>
                          <div className="body">
                            {(item.evidence || []).map((e, k) => (
                              <p key={k} className="quote">
                                <button type="button" className="evidence-time" onClick={() => seek(e.t)}>{e.t}</button>
                                {e.quote ? `“${e.quote}”` : e.signal}
                              </p>
                            ))}
                            {item.tip && <p className="try"><b>Try:</b> {item.tip}</p>}
                          </div>
                        </details>
                      </li>
                    ))}
                  </ol>
                </section>
              )}
              {s && (
                <section className="sec">
                  <div className="sec-head"><h2 className="display">Whole interview</h2><p>Strengths and dimensions</p></div>
                  <EvidenceFeedback result={{ ...s, transcript: report.transcript }} onSeek={seek} hideImprovements={todo.length} />
                </section>
              )}
            </>
          )}

          {(answers.length > 0 || (streaming && pending > 0)) && (
            <section className="sec">
              <div className="sec-head"><h2 className="display">By question</h2><p>Tap a question to open it</p></div>
              {answers.map((a, i) => (
                <details key={i} className="answer-block" open={i === 0}>
                  <summary className="answer-head">
                    <span className="answer-time mono">{streaming ? mmss(Number(a.asked_at) || 0) : `Q${i + 1} · ${mmss(Number(a.asked_at) || 0)}`}</span>
                    <span className="answer-q">{a.question}</span>
                    <span className="answer-score mono">{a.score ?? '—'}</span>
                  </summary>
                  <EvidenceFeedback result={a} onSeek={seek} />
                </details>
              ))}
              {streaming && Array.from({ length: pending }, (_, i) => <div key={`p${i}`} className="skeleton skeleton-row" aria-busy="true" />)}
            </section>
          )}

          <footer className="doc-end">
            <button type="button" className="btn btn-lg" onClick={onRestart}>Practice again</button>
            <button type="button" className="btn btn-ghost" onClick={onHome}>Back to home</button>
          </footer>
        </article>
      </main>
    </div>
  );
}
