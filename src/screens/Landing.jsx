import React from 'react';

// One headline, one primary action. Quick Practice stays reachable through the small secondary link.
// Copy follows docs/product-polish/spec.md section 2.1.
export default function Landing({ onStart, onPractice }) {
  return (
    <main className="app-container landing">
      <h1>Practice out loud with an interviewer who follows up.</h1>
      <p className="subtitle">It asks about your resume, follows up on what you say, then shows you the exact moments to work on.</p>
      <button type="button" className="btn btn-submit landing-cta" onClick={onStart}>Start mock interview</button>
      <ol className="landing-steps">
        <li><strong>Drop your resume</strong><br />Optional. The interviewer asks about your real experience.</li>
        <li><strong>Pick an interview type</strong><br />Academic, Career or Social.</li>
        <li><strong>Talk it through</strong><br />Answer out loud. Get a report that points to the exact moments.</li>
      </ol>
      <button type="button" className="link-btn" onClick={onPractice}>Or practice a single question</button>
    </main>
  );
}
