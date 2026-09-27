import React, { useRef } from 'react';
import EvidenceFeedback from './EvidenceFeedback';

const secs = (mmss) => { const [m, s] = String(mmss).split(':').map(Number); return m * 60 + s; };
const mmss = (t) => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;

// Report for a whole live interview: one summary on top, then each question with its own feedback.
// Every timestamp jumps the recording to that moment.
export default function SessionReport({ report, audioURL, onRestart, onHome }) {
  const player = useRef(null);
  const seek = (t) => {
    if (!player.current || Number.isNaN(secs(t))) return;
    player.current.currentTime = secs(t);
    player.current.play().catch(() => {});
  };
  const s = report.summary;

  return (
    <div className="session-report">
      {audioURL && <audio ref={player} src={audioURL} controls className="audio-player" />}

      {!s ? <p className="coverage-note">{report.note || 'No answers were found in the recording.'}</p> : (
        <section className="session-summary">
          <h3>Whole interview</h3>
          <div className="session-score">
            <span className="session-score-number">{s.score ?? '—'}</span><span className="session-score-max">/100</span>
          </div>
          <EvidenceFeedback result={{ ...s, transcript: report.transcript }} onSeek={seek} />
        </section>
      )}

      {report.answers.map((a, i) => (
        <details key={i} className="answer-block" open={i === 0}>
          <summary className="answer-head">
            <span className="answer-time">Q{i + 1} · {mmss(a.asked_at)}</span>
            <span>{a.question}</span>
            <span className="answer-score">{a.score ?? '—'}</span>
          </summary>
          <EvidenceFeedback result={a} onSeek={seek} />
        </details>
      ))}

      <div className="result-actions">
        <button type="button" className="btn btn-secondary" onClick={onRestart}>🔄 New interview</button>
        <button type="button" className="btn btn-secondary" onClick={onHome}>🏠 Back to Home</button>
      </div>
    </div>
  );
}
