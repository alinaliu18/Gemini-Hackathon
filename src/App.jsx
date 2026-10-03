import React, { useState } from 'react';
import './App.css';
import LiveInterview from './components/LiveInterview';
import SessionReport from './components/SessionReport';
import Landing from './screens/Landing';
import Setup from './screens/Setup';
import QuickPractice from './screens/QuickPractice';

const API_BASE_URL = 'http://localhost:5002';

// Main path: landing -> setup -> live -> report. Quick Practice ('practice') is only reachable from the landing link.
function App() {
  const [screen, setScreen] = useState('landing'); // landing | setup | live | report | practice

  // Shared inputs: Setup fills them, the live interview and Quick Practice send them to the backend.
  const [ageGroup, setAgeGroup] = useState('');
  const [interviewGoal, setInterviewGoal] = useState('');
  const [resumeFile, setResumeFile] = useState(null);
  const [contextText, setContextText] = useState('');

  const [session, setSession] = useState(null); // {report, audioURL} from a live interview

  return (
    <div className="app">
      {screen === 'landing' && <Landing onStart={() => setScreen('setup')} onPractice={() => setScreen('practice')} />}

      {screen === 'setup' && (
        <Setup goal={interviewGoal} setGoal={setInterviewGoal} resumeFile={resumeFile} setResumeFile={setResumeFile}
               ageGroup={ageGroup} setAgeGroup={setAgeGroup} contextText={contextText} setContextText={setContextText}
               onStart={() => setScreen('live')} onBack={() => setScreen('landing')} onPractice={() => setScreen('practice')} />
      )}

      {screen === 'live' && (
        <>
          <header className="app-header step-header">
            <h1>Live Interview</h1>
            <p className="subtitle">Talk it through like the real thing. Interrupt, ask to repeat, take your time.</p>
          </header>
          <main className="app-container">
            <LiveInterview apiBase={API_BASE_URL} goal={interviewGoal} contextText={contextText} resumeFile={resumeFile}
                           onBack={() => setScreen('setup')}
                           onReport={(report, audioURL) => { setSession({ report, audioURL }); setScreen('report'); }} />
          </main>
        </>
      )}

      {screen === 'report' && session && (
        <>
          <header className="app-header step-header">
            <h1>📊 Your Interview Report</h1>
            <p className="subtitle">Every point links to the moment it is based on</p>
          </header>
          <main className="app-container">
            <SessionReport report={session.report} audioURL={session.audioURL}
                           onRestart={() => { setSession(null); setScreen('live'); }}
                           onHome={() => { setSession(null); setScreen('landing'); }} />
          </main>
        </>
      )}

      {screen === 'practice' && (
        <QuickPractice apiBase={API_BASE_URL} goal={interviewGoal} ageGroup={ageGroup} contextText={contextText}
                       resumeFile={resumeFile} onHome={() => setScreen('landing')} onLive={() => setScreen('setup')} />
      )}
    </div>
  );
}

export default App;
