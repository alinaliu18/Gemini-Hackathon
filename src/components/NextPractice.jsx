import React, { useState } from 'react';
import { apiFetch } from '../api';

// After a report: suggest the next practice on the weakest scored part. Nothing is created until the person agrees;
// then the backend saves the plan and returns a calendar invite whose link opens a practice that starts on that part.
const pad = (n) => String(n).padStart(2, '0');
// Tomorrow at this hour, or 6 pm when this hour is outside 9 am to 9 pm.
function tomorrowLocal() {
  const d = new Date(Date.now() + 24 * 3600 * 1000);
  if (d.getHours() < 9 || d.getHours() > 21) d.setHours(18);
  d.setMinutes(0, 0, 0);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:00`;
}

export default function NextPractice({ apiBase, runId, suggestion }) {
  const [when, setWhen] = useState(tomorrowLocal);
  const [state, setState] = useState('ask'); // ask | saving | done | declined | error
  const [plan, setPlan] = useState(null);
  const [error, setError] = useState('');
  if (!runId || !suggestion) return null;

  async function agree() {
    setState('saving');
    setError('');
    try {
      const res = await apiFetch(apiBase, '/api/next_session', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ run_id: runId, starts_at: new Date(when).toISOString() }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || `That did not work (${res.status}).`);
      setPlan(data);
      setState('done');
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([data.ics], { type: 'text/calendar' }));
      a.download = 'interview-practice.ics';
      document.body.appendChild(a); a.click(); a.remove();
    } catch (e) {
      setState('error');
      setError(e instanceof TypeError ? "Can't reach the backend. Try again in a moment." : e.message);
    }
  }

  if (state === 'declined') return null;
  return (
    <section className="next-practice" aria-labelledby="next-practice-title">
      <span className="label">Next practice</span>
      <h2 id="next-practice-title">Work on {suggestion.label.toLowerCase()} next</h2>
      {state === 'done' ? (
        <>
          <p>Saved. Open the invite file that just downloaded to add it to your calendar. When you open the link, the first question will be about {plan.how}.</p>
          <p className="next-link mono">{plan.link}</p>
        </>
      ) : (
        <>
          <p>It was your lowest score this time ({suggestion.score}). Next time the first question will be about {suggestion.how}.</p>
          <div className="next-row">
            <label>When
              <input type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} />
            </label>
            <button type="button" className="btn" disabled={state === 'saving' || !when} onClick={agree}>
              {state === 'saving' ? 'Saving' : 'Add to my calendar'}
            </button>
            <button type="button" className="btn btn-ghost" onClick={() => setState('declined')}>Not now</button>
          </div>
          {error && <p className="jd-note is-error" role="alert">{error}</p>}
        </>
      )}
    </section>
  );
}
