import React from 'react';

// Every feedback line shows the moment it is based on, so users can check it instead of trusting a vague verdict.
const LABELS = {
  content: 'Content', structure: 'Structure (STAR)', clarity: 'Clarity', pacing: 'Pacing',
  filler_words: 'Filler words', eye_contact: 'Eye contact', presence: 'Presence',
};

function Evidence({ items, onSeek }) {
  if (!items?.length) return null;
  return (
    <ul className="evidence-list">
      {items.map((e, i) => (
        <li key={i}>
          <button type="button" className="evidence-time" onClick={() => onSeek?.(e.t)} title="Jump to this moment">{e.t}</button>
          <span className="evidence-text">{e.quote ? `“${e.quote}”` : e.signal}</span>
        </li>
      ))}
    </ul>
  );
}

export default function EvidenceFeedback({ result, onSeek, hideImprovements = 0 }) {
  if (!result?.dimensions) return null;
  const coverage = result.score_coverage;
  return (
    <div className="evidence-feedback">
      {coverage != null && coverage < 0.8 && (
        <p className="coverage-note">
          Partial score: based on {Math.round(coverage * 100)}% of the rubric
          ({(result.not_measured || []).map((k) => LABELS[k] || k).join(', ')} could not be measured).
        </p>
      )}

      {result.strengths?.length > 0 && (
        <section>
          <h4>What went well</h4>
          {result.strengths.map((s, i) => (
            <div key={i} className="feedback-item good">
              <p>{s.text}</p>
              <Evidence items={s.evidence} onSeek={onSeek} />
            </div>
          ))}
        </section>
      )}

      {result.improvements?.length > hideImprovements && (
        <section>
          <h4>{hideImprovements ? 'Also worth a look' : 'To work on'}</h4>
          {result.improvements.slice(hideImprovements).map((s, i) => (
            <div key={i} className="feedback-item improve">
              <p>{s.text}</p>
              {s.tip && <p className="tip"><b>Try:</b> {s.tip}</p>}
              <Evidence items={s.evidence} onSeek={onSeek} />
            </div>
          ))}
        </section>
      )}

      <section>
        <h4>By dimension</h4>
        {Object.entries(result.dimensions).map(([k, d]) => (
          <div key={k} className="dimension-row">
            <div className="dimension-head">
              <span className="dimension-name">{LABELS[k] || k}</span>
              <span className="dimension-score">{d.score ?? '—'}</span>
            </div>
            <p className="dimension-obs">{d.observation}</p>
            <Evidence items={d.evidence} onSeek={onSeek} />
          </div>
        ))}
      </section>

      {result.transcript?.length > 0 && (
        <details className="transcript">
          <summary>Transcript</summary>
          {result.transcript.map((s, i) => (
            <p key={i}><button type="button" className="evidence-time" onClick={() => onSeek?.(s.t)}>{s.t}</button> {s.text}</p>
          ))}
        </details>
      )}
    </div>
  );
}
