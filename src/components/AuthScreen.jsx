import React, { useEffect, useRef, useState } from 'react';
import { apiFetch, setToken } from '../api';

// The first practice is free; after that an account is needed. A dialog over whatever the person was doing, so
// signing in does not lose the resume and the job description they filled in.
export default function AuthScreen({ apiBase, message, onDone, onClose }) {
  const [mode, setMode] = useState('signup'); // signup | login
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const emailRef = useRef(null);
  useEffect(() => { emailRef.current?.focus(); }, []);

  async function submit(e) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      const res = await apiFetch(apiBase, `/api/auth/${mode}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || `That did not work (${res.status}). Try again.`);
      setToken(data.token);
      onDone(data.email, mode);
    } catch (err) {
      setError(err instanceof TypeError ? "Can't reach the backend. Start it with `npm start`, then try again." : err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-overlay" onKeyDown={(e) => { if (e.key === 'Escape') onClose(); }}>
      <form className="auth-card" role="dialog" aria-modal="true" aria-labelledby="auth-title" onSubmit={submit}>
        <h2 id="auth-title" className="display">{mode === 'signup' ? 'Create a free account' : 'Sign in'}</h2>
        <p className="auth-lead">{message || 'Your practices are saved to your account, so you can see how you improve.'}</p>
        <label className="auth-field">Email
          <input ref={emailRef} type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label className="auth-field">Password
          <input type="password" required minLength={mode === 'signup' ? 8 : undefined}
                 autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                 value={password} onChange={(e) => setPassword(e.target.value)} />
          {mode === 'signup' && <small className="hint">At least 8 characters.</small>}
        </label>
        {error && <p className="jd-note is-error" role="alert">{error}</p>}
        <button type="submit" className="btn btn-lg" disabled={busy}>
          {busy ? 'One moment' : mode === 'signup' ? 'Create account' : 'Sign in'}
        </button>
        <p className="auth-switch">
          {mode === 'signup' ? 'Already have an account? ' : 'New here? '}
          <button type="button" className="link-btn" onClick={() => { setMode(mode === 'signup' ? 'login' : 'signup'); setError(''); }}>
            {mode === 'signup' ? 'Sign in' : 'Create an account'}
          </button>
        </p>
        <button type="button" className="btn btn-ghost btn-sm auth-close" onClick={onClose}>Not now</button>
      </form>
    </div>
  );
}
