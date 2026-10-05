import React from 'react';
import './screens.css';

// One promise, one primary action. The transcript card shows the follow-up instead of describing it.
// Quick Practice stays reachable through the secondary link.
export default function Landing({ onStart, onPractice }) {
  return (
    <div className="screen-page">
      <TopBar />
      <main className="landing">
        <div className="landing-copy">
          <h1 className="display">Practice out loud with an interviewer who <em>follows up.</em></h1>
          <p className="lead">It asks about your resume, listens to your answer, and asks the next question a real interviewer would. Every note in your report links to the moment you said it.</p>
          <div className="cta-row">
            <button type="button" className="btn btn-lg" onClick={onStart}>Start mock interview</button>
            <button type="button" className="btn btn-ghost" onClick={onPractice}>Practice one question</button>
          </div>
          <p className="privacy">
            <svg className="icon" viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="10.5" width="14" height="10" rx="2" /><path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5" /></svg>
            Your video stays on your device. Only measurements like "facing camera 74%" are sent.
          </p>
        </div>

        <figure className="landing-transcript" aria-label="Example transcript">
          <div className="landing-transcript-head"><span className="live"><span className="dot" />Live transcript</span><span className="mono">Career track</span></div>
          <div className="turn interviewer">
            <span className="who">Interviewer <span className="mono">2:02</span></span>
            <p>Tell me about a decision from your product internship that changed the product.</p>
          </div>
          <div className="turn you">
            <span className="who">You <span className="mono">2:14</span></span>
            <p>We kind of decided as a team to cut the second onboarding screen, and, um, it worked out.</p>
          </div>
          <div className="turn followup">
            <span className="who"><b>Follow-up</b><span className="mono">2:31</span>
              <span className="wave" aria-hidden="true">{[6, 12, 16, 9, 14, 7, 12, 16, 10, 6, 11, 5].map((h, i) => <i key={i} style={{ height: h }} />)}</span>
            </span>
            <p>You said the team decided. What was your part in that decision?</p>
          </div>
          <p className="landing-transcript-foot">Follow-ups come from what you actually said, not from a fixed list.</p>
        </figure>

        <ol className="steps">
          <li><span className="num display">1</span><b>Drop your resume</b><span>Optional. Questions come from it.</span></li>
          <li><span className="num display">2</span><b>Pick a track</b><span>Academic, Career, or Social.</span></li>
          <li><span className="num display">3</span><b>Talk</b><span>About 5 to 8 minutes, by voice. Then read your report.</span></li>
        </ol>
      </main>
    </div>
  );
}

export function TopBar({ onHome }) {
  return (
    <header className="topbar">
      <button type="button" className="wordmark" onClick={onHome} disabled={!onHome}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="1" y="1" width="22" height="22" rx="7" fill="#1D4CF5" /><path d="M6.5 12h1.4M9.8 8.5v7M13.1 10v4M16.4 7.5v9" stroke="#FFFFFF" strokeWidth="1.9" strokeLinecap="round" fill="none" /></svg>
        Interview Maestro
      </button>
    </header>
  );
}
