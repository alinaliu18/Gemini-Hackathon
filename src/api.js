// The one place that talks to the backend. It says who is asking, with a random id this browser keeps and the
// sign-in token when there is one, and it tells the app when the backend answers "sign in to keep practicing".
// Storage can be unavailable (private windows, blocked site data), so every read and write is guarded.

const VISITOR_KEY = 'maestro.visitor';
const TOKEN_KEY = 'maestro.token';
export const LOGIN_EVENT = 'maestro:login-required';

const read = (k) => { try { return localStorage.getItem(k); } catch { return null; } };
const write = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch { /* storage blocked */ } };

let memoryVisitor = null; // used when storage is blocked, so one page load still has one id
export function visitorId() {
  let id = read(VISITOR_KEY) || memoryVisitor;
  if (!id) {
    id = (crypto.randomUUID && crypto.randomUUID()) || `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}-0000`;
    memoryVisitor = id;
    write(VISITOR_KEY, id);
  }
  return id;
}

export const getToken = () => read(TOKEN_KEY);
export const setToken = (t) => write(TOKEN_KEY, t);

export async function apiFetch(base, path, init = {}) {
  const headers = new Headers(init.headers || {});
  headers.set('X-Visitor-Id', visitorId());
  const token = getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const res = await fetch(`${base}${path}`, { ...init, headers });
  if (res.status === 401) {
    const body = await res.clone().json().catch(() => ({}));
    if (body.reason === 'login_required') window.dispatchEvent(new CustomEvent(LOGIN_EVENT, { detail: body.error }));
  }
  return res;
}

// Product events for the funnel. Fire and forget: a failed event is never shown to anyone. Only a name and a few short
// facts are sent, never what was said or typed.
const sent = new Set();
export function track(base, name, props = {}, { once = false } = {}) {
  if (once) {
    if (sent.has(name)) return;
    sent.add(name);
  }
  apiFetch(base, '/api/event', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, props }), keepalive: true,
  }).catch(() => {});
}
