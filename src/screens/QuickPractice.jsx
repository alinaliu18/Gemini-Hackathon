import React, { useState, useEffect, useRef } from 'react';
import EvidenceFeedback from '../components/EvidenceFeedback';
import { TopBar } from './Landing';
import './session.css';
import { createFaceSignalTracker } from '../signals/faceSignals';
import { aggregateSignals } from '../signals/aggregate';

// Secondary path: one question, answered by voice or text, scored with the same evidence pipeline.
// Reached only from the landing page's "Practice one question" link.
export default function QuickPractice({ apiBase, goal, contextText, resumeFile, onHome, onLive }) {
  const [textInput, setTextInput] = useState('');

  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioURL, setAudioURL] = useState(null);

  const [cameraOn, setCameraOn] = useState(true);
  const [videoSignals, setVideoSignals] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState('');
  const [asked, setAsked] = useState([]);
  const [questionLoading, setQuestionLoading] = useState(false);
  const [error, setError] = useState(null);

  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const trackerRef = useRef(null);
  const videoRef = useRef(null);
  const playbackRef = useRef(null);

  const startRecording = async () => {
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: cameraOn });
    } catch (err) {
      if (!cameraOn) {
        console.error('Error accessing microphone:', err);
        setError('Could not access microphone. Please check permissions.');
        return;
      }
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });  // camera refused: still record audio
        setCameraOn(false);
      } catch (err2) {
        console.error('Error accessing microphone:', err2);
        setError('Could not access microphone. Please check permissions.');
        return;
      }
    }
    streamRef.current = stream;
    setVideoSignals(null);

    // Only audio is recorded and uploaded; video stays on this device.
    mediaRecorderRef.current = new MediaRecorder(new MediaStream(stream.getAudioTracks()));
    const audioChunks = [];
    mediaRecorderRef.current.ondataavailable = (event) => {
      if (event.data.size > 0) audioChunks.push(event.data);
    };
    mediaRecorderRef.current.onstop = () => {
      const type = mediaRecorderRef.current.mimeType || 'audio/webm';
      const blob = new Blob(audioChunks, { type });
      setAudioBlob(blob);
      setAudioURL(URL.createObjectURL(blob));
    };
    mediaRecorderRef.current.start();
    setIsRecording(true);
    setError(null);

    if (stream.getVideoTracks().length && videoRef.current) {
      videoRef.current.srcObject = stream;
      await videoRef.current.play().catch(() => {});
      trackerRef.current = await createFaceSignalTracker(videoRef.current);
      trackerRef.current?.start();
    }
  };

  const stopRecording = () => {
    if (!mediaRecorderRef.current || !isRecording) return;
    mediaRecorderRef.current.stop();
    setIsRecording(false);
    if (trackerRef.current) {
      const samples = trackerRef.current.stop();
      trackerRef.current = null;
      if (samples.length) setVideoSignals(aggregateSignals(samples));
    }
    streamRef.current?.getTracks().forEach((tr) => tr.stop());
    if (videoRef.current) videoRef.current.srcObject = null;
  };

  // Leaving mid-recording releases mic and camera.
  useEffect(() => () => {
    trackerRef.current?.stop();
    streamRef.current?.getTracks().forEach((tr) => tr.stop());
  }, []);

  // Jump the answer playback to an "m:ss" timestamp from the feedback.
  const seekTo = (mmss) => {
    const [m, s] = String(mmss).split(':').map(Number);
    if (playbackRef.current && !Number.isNaN(m) && !Number.isNaN(s)) {
      playbackRef.current.currentTime = m * 60 + s;
      playbackRef.current.play().catch(() => {});
    }
  };

  // Quick Practice asks one question built from the uploaded resume (or the context box).
  const fetchQuestion = async () => {
    setQuestionLoading(true);
    try {
      const form = new FormData();
      form.append('goal', goal);
      form.append('context_text', contextText);
      form.append('avoid', asked.join(' | '));
      if (resumeFile) form.append('file', resumeFile);
      const res = await fetch(`${apiBase}/api/question`, { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || `Question failed (${res.status})`);
      setQuestion(data.question);
      setAsked((a) => [...a, data.question]);
    } catch (e) {
      setError(e instanceof TypeError ? "Can't reach the backend. Start it with `npm start`, then try again." : e.message);
    } finally {
      setQuestionLoading(false);
    }
  };

  // The ref keeps React StrictMode's dev double-mount from requesting two questions.
  const fetched = useRef(false);
  useEffect(() => { if (!fetched.current) { fetched.current = true; fetchQuestion(); } }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Track is optional here: the backend defaults it to Career.
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!textInput && !audioBlob) {
      setError('Please provide either text or audio response');
      return;
    }

    setLoading(true);
    setError(null);
    setEvaluation(null);

    try {
      const formData = new FormData();
      formData.append('goal', goal);
      formData.append('sub_type', 'Interview');
      formData.append('text_input', textInput);
      formData.append('context_text', contextText);
      formData.append('question', question || contextText);
      if (videoSignals) formData.append('video_signals', JSON.stringify(videoSignals));

      if (resumeFile) {
        formData.append('file', resumeFile);
      }

      if (audioBlob) {
        const ext = audioBlob.type.includes('mp4') ? 'm4a' : audioBlob.type.includes('ogg') ? 'ogg' : 'webm';
        formData.append('audio_response', audioBlob, `answer.${ext}`);
      }

      const response = await fetch(`${apiBase}/api/evaluate`, {
        method: 'POST',
        body: formData,
        headers: {
          'Accept': 'application/json'
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.evaluation || `Server error: ${response.status}`);
      }

      const data = await response.json();
      setEvaluation(data);

    } catch (err) {
      console.error('Submission error:', err);
      setError(`Failed to evaluate: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (evaluation) {
    return (
      <div className="screen-page">
        <TopBar onHome={onHome} />
        <main className="practice">
          <section className="results-section">
            <div className="practice-title">
              <h1 className="display">Your feedback</h1>
              <p>Every point links to the moment it is based on.</p>
            </div>
            <div className="score-card">
              <div className="score-display">
                <span className="score-number display">{evaluation.score}</span>
                <span className="score-max">/ 100</span>
              </div>
              <div className="score-bar">
                <div className="score-fill" style={{width: `${evaluation.score}%`}} />
              </div>
            </div>

            {audioURL && (
              <div className="audio-playback">
                <audio ref={playbackRef} src={audioURL} controls className="audio-player" />
              </div>
            )}

            <EvidenceFeedback result={evaluation} onSeek={seekTo} />

            <div className="result-actions">
              <button
                type="button"
                onClick={() => {
                  setEvaluation(null);
                  setTextInput('');
                  setAudioBlob(null);
                  setAudioURL(null);
                  setVideoSignals(null);
                }}
                className="btn btn-secondary"
              >
                Try again
              </button>
              <button type="button" onClick={onLive} className="btn">
                Try the live interview
              </button>
              <button type="button" onClick={onHome} className="btn btn-secondary">
                Back to home
              </button>
            </div>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="screen-page">
      <TopBar onHome={onHome} />
      <main className="practice">
        <div className="practice-title">
          <h1 className="display">Practice one question</h1>
          <p>Answer out loud or type it. You get feedback in under a minute.</p>
        </div>
        <section className="question-card">
          <span className="question-label">{resumeFile ? 'Question from your resume' : 'Question'}</span>
          <p className="question-text">{questionLoading ? 'Writing a question…' : (question || 'No question yet.')}</p>
          <button type="button" className="btn btn-secondary question-new" onClick={fetchQuestion} disabled={questionLoading}>New question</button>
        </section>
        <form className="practice-form" onSubmit={handleSubmit}>
          <div className="response-section">
            <div className="audio-section">
              <h3>Say it out loud</h3>
              <div className="camera-panel">
                <label>
                  <input type="checkbox" checked={cameraOn} disabled={isRecording}
                         onChange={(e) => setCameraOn(e.target.checked)} /> Use camera for eye contact &amp; presence
                </label>
                <video ref={videoRef} className="camera-preview" muted playsInline hidden={!isRecording || !cameraOn} />
                {cameraOn && <p className="camera-note">Analysed on your device. Video is never uploaded; only numbers like "eye contact 72%" are sent.</p>}
                {videoSignals && !isRecording && (
                  <p className="camera-note">Captured: face in frame {Math.round(videoSignals.face_present_ratio * 100)}%, facing camera {Math.round(videoSignals.eye_contact_ratio * 100)}%.</p>
                )}
              </div>
              <div className="recording-area">
                {!isRecording ? (
                  <button
                    type="button"
                    onClick={startRecording}
                    className="record-btn"
                  >
                    <span className="record-icon" />
                    Start recording
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={stopRecording}
                    className="record-btn recording"
                  >
                    <span className="stop-icon" />
                    Stop recording
                  </button>
                )}
                {audioURL && (
                  <div className="audio-playback">
                    <audio src={audioURL} controls className="audio-player" />
                  </div>
                )}
              </div>
            </div>

            <div className="or-divider">or</div>

            <div className="text-section">
              <h3>Type it</h3>
              <textarea
                placeholder="Type your answer here."
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                className="response-textarea"
                rows="8"
              />
            </div>
          </div>

          {error && (
            <div className="alert alert-error">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="btn btn-submit"
            disabled={loading || (!textInput && !audioBlob)}
          >
            {loading ? 'Analyzing…' : 'Get feedback'}
          </button>
        </form>
      </main>
    </div>
  );
}
