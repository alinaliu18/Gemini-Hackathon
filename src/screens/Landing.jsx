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
            <a className="btn btn-secondary btn-lg" href="#how">See how it works</a>
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

      </main>

      <section className="lp-section" id="how">
        <div className="lp-inner">
          <h2 className="display">Three steps. Under a minute to set up.</h2>
          <ol className="steps">
            <li><span className="num display">1</span><b>Drop your resume</b><span>Optional. The interviewer picks questions from your real projects and jobs.</span></li>
            <li><span className="num display">2</span><b>Pick a track</b><span>Academic, Career, or Social. Each one has its own questions and pace range.</span></li>
            <li><span className="num display">3</span><b>Talk</b><span>About 5 to 8 minutes, by voice. You can interrupt, ask it to repeat, or take your time.</span></li>
          </ol>
        </div>
      </section>

      <section className="lp-section lp-tint">
        <div className="lp-inner lp-split">
          <div className="lp-copy">
            <h2 className="display">Feedback you can check.</h2>
            <p className="lead">Vague advice like "be more confident" is hard to act on. Every note in your report points to the second you said it.</p>
            <ul className="lp-points">
              <li><b>Measured in code.</b> Pace in words per minute, long pauses, filler words, and background noise are counted, not guessed.</li>
              <li><b>Quotes are verified.</b> Each note cites a time and your exact words. Notes with a quote that was not said are dropped.</li>
              <li><b>No mind reading.</b> It reports what it can observe, like "3 pauses over 4 seconds", and never says you seem nervous.</li>
            </ul>
          </div>
          <figure className="lp-card" aria-label="Example report note">
            <div className="lp-card-head"><span className="label">To work on</span><span className="chip chip-warning">Action</span></div>
            <h3>Name your own part before the team's.</h3>
            <p className="lp-quote"><span className="evidence-time">2:14</span>“We kind of decided as a team to cut the second onboarding screen, and, um, it worked out.”</p>
            <p className="lp-try"><b>Try:</b> open with one sentence about what you did. "I ran six user calls and proposed cutting step 2."</p>
          </figure>
        </div>
      </section>

      <section className="lp-section">
        <div className="lp-inner">
          <h2 className="display">Pick the interview you are preparing for.</h2>
          <div className="lp-tracks">
            <div><b className="display">Academic</b><span>College, scholarship, and grad school interviews.</span></div>
            <div><b className="display">Career</b><span>Internships and jobs. Behavioral and resume questions.</span></div>
            <div><b className="display">Social</b><span>Clubs, student orgs, and volunteer roles.</span></div>
          </div>
        </div>
      </section>

      <section className="lp-cta" id="start">
        <div className="lp-cta-inner">
          <h2 className="display">Ready for the first question?</h2>
          <p>About a minute to set up, 5 to 8 minutes to talk, then your report.</p>
          <button type="button" className="lp-cta-btn" onClick={onStart}>Start mock interview</button>
          <button type="button" className="lp-cta-link" onClick={onPractice}>Or practice one question</button>
        </div>
      </section>
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
