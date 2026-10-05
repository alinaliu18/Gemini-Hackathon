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
  // #setup opens Setup directly (handy for screenshots and sharing); every other screen needs state from earlier ones.
  const [screen, setScreen] = useState(() => (window.location.hash === '#setup' ? 'setup' : 'landing')); // landing | setup | live | report | practice

  // Shared inputs: Setup fills them, the live interview and Quick Practice send them to the backend.
  const [interviewGoal, setInterviewGoal] = useState('');
  const [resumeFile, setResumeFile] = useState(null);
  const [contextText, setContextText] = useState('');

  const [session, setSession] = useState(null); // {report, audioURL} from a live interview

  return (
    <div className="app">
      {screen === 'landing' && <Landing onStart={() => setScreen('setup')} onPractice={() => setScreen('practice')} />}

      {screen === 'setup' && (
        <Setup goal={interviewGoal} setGoal={setInterviewGoal} resumeFile={resumeFile} setResumeFile={setResumeFile}
               contextText={contextText} setContextText={setContextText}
               onStart={() => setScreen('live')} onBack={() => setScreen('landing')} onPractice={() => setScreen('practice')} />
      )}

      {screen === 'live' && (
        <LiveInterview apiBase={API_BASE_URL} goal={interviewGoal} contextText={contextText} resumeFile={resumeFile}
                       onBack={() => setScreen('setup')}
                       onReport={(report, audioURL) => { setSession({ report, audioURL }); setScreen('report'); }} />
      )}

      {screen === 'report' && session && (
        <SessionReport report={session.report} audioURL={session.audioURL}
                       onRestart={() => { setSession(null); setScreen('setup'); }}
                       onHome={() => { setSession(null); setScreen('landing'); }} />
      )}

      {screen === 'practice' && (
        <QuickPractice apiBase={API_BASE_URL} goal={interviewGoal} contextText={contextText}
                       resumeFile={resumeFile} onHome={() => setScreen('landing')} onLive={() => setScreen('setup')} />
      )}
    </div>
  );
}

export default App;
