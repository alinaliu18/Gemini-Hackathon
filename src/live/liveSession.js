// Browser side of the live interview: mic -> Gemini Live, Gemini's voice -> speakers, plus captions and turn timing.
// The token comes from our backend (/api/live/token) with the interviewer's instructions locked in; the API key never
// reaches the browser. All times are seconds since the session clock started (same clock as the candidate recording).

const wsUrl = (token) =>
  'wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.' +
  `BidiGenerateContentConstrained?access_token=${encodeURIComponent(token)}`;

// Converts mic samples to 16-bit PCM and posts ~100 ms chunks. Sent at the context's own sample rate:
// the Live API resamples when the mime type names the rate.
const CAPTURE_WORKLET = `
class Pcm16Capture extends AudioWorkletProcessor {
  constructor() { super(); this.buf = []; this.size = Math.round(sampleRate / 10); }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (ch) for (let i = 0; i < ch.length; i++) this.buf.push(ch[i]);
    if (this.buf.length >= this.size) {
      const out = new Int16Array(this.buf.length);
      for (let i = 0; i < out.length; i++) { const s = Math.max(-1, Math.min(1, this.buf[i])); out[i] = s < 0 ? s * 0x8000 : s * 0x7fff; }
      this.port.postMessage(out.buffer, [out.buffer]);
      this.buf = [];
    }
    return true;
  }
}
registerProcessor('pcm16-capture', Pcm16Capture);`;

const OUTPUT_RATE = 24000; // Live API voice output: 16-bit PCM, 24 kHz
const END_PHRASE = /report is being prepared/i;

export function toBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

export function pcm16ToFloat(b64) {
  const bin = atob(b64);
  const out = new Float32Array(bin.length >> 1);
  for (let i = 0; i < out.length; i++) {
    const v = bin.charCodeAt(2 * i) | (bin.charCodeAt(2 * i + 1) << 8);
    out[i] = (v >= 0x8000 ? v - 0x10000 : v) / 0x8000;
  }
  return out;
}

/**
 * Start a live interview on an existing mic stream.
 * onCaptions(list of {role: 'interviewer'|'candidate', text}), onStatus('live'|'ended'|'error', detail), onInterviewDone()
 * Returns { clock() -> seconds since start, stop() -> turns }.
 */
export async function startLiveSession({ token, model, stream, onCaptions, onStatus, onInterviewDone }) {
  const ctx = new AudioContext();
  await ctx.resume();
  const t0 = ctx.currentTime;
  const clock = () => +(ctx.currentTime - t0).toFixed(2);

  const turns = [];         // interviewer turns: {role, start, end, text, interrupted}
  const captions = [];
  let turn = null;          // interviewer turn being spoken
  let playAt = 0;           // context time where the next voice chunk starts
  let sources = [];
  let closed = false;
  const emit = () => onCaptions?.(captions.map((c) => ({ ...c })));
  const caption = (role, text) => {
    const last = captions[captions.length - 1];
    if (last && last.role === role) last.text += text;
    else captions.push({ role, text });
    emit();
  };

  const ws = new WebSocket(wsUrl(token));
  await new Promise((resolve, reject) => {
    ws.onopen = () => ws.send(JSON.stringify({ setup: { model: `models/${model}` } })); // rest of the config is in the token
    ws.onerror = () => reject(new Error('Could not connect to the live interviewer.'));
    ws.onclose = (e) => reject(new Error(`Live connection closed: ${e.reason || e.code}`));
    ws.onmessage = async (ev) => {
      const msg = JSON.parse(typeof ev.data === 'string' ? ev.data : await ev.data.text());
      if (msg.setupComplete) resolve();
    };
  });

  const finishTurn = (interrupted) => {
    if (!turn) return;
    turn.interrupted = interrupted;
    turn.end = interrupted ? clock() : +Math.max(clock(), playAt - t0).toFixed(2);
    turn.text = turn.text.trim();
    turns.push(turn);
    const done = !interrupted && END_PHRASE.test(turn.text);
    turn = null;
    if (done) setTimeout(() => onInterviewDone?.(), Math.max(0, (playAt - ctx.currentTime) * 1000) + 300);
  };

  ws.onmessage = async (ev) => {
    const msg = JSON.parse(typeof ev.data === 'string' ? ev.data : await ev.data.text());
    const sc = msg.serverContent;
    if (msg.goAway) onStatus?.('live', 'The session is about to time out; wrap up soon.');
    if (!sc) return;
    for (const part of sc.modelTurn?.parts || []) {
      if (!part.inlineData?.data) continue;
      const samples = pcm16ToFloat(part.inlineData.data);
      const buf = ctx.createBuffer(1, samples.length, OUTPUT_RATE);
      buf.copyToChannel(samples, 0);
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.connect(ctx.destination);
      playAt = Math.max(playAt, ctx.currentTime);
      if (!turn) turn = { role: 'interviewer', start: +(playAt - t0).toFixed(2), text: '' };
      src.start(playAt);
      playAt += buf.duration;
      sources.push(src);
      src.onended = () => { sources = sources.filter((s) => s !== src); };
    }
    if (sc.outputTranscription?.text) {
      if (!turn) turn = { role: 'interviewer', start: clock(), text: '' };
      turn.text += sc.outputTranscription.text;
      caption('interviewer', sc.outputTranscription.text);
    }
    if (sc.inputTranscription?.text) caption('candidate', sc.inputTranscription.text);
    if (sc.interrupted) { // candidate started talking: stop the interviewer's voice right away
      sources.forEach((s) => { try { s.stop(); } catch { /* already stopped */ } });
      sources = [];
      playAt = ctx.currentTime;
      finishTurn(true);
    }
    if (sc.turnComplete) finishTurn(false);
  };
  ws.onclose = (e) => { if (!closed) onStatus?.('error', `Live connection closed: ${e.reason || e.code}`); };

  // mic -> 16-bit PCM chunks -> Live API
  await ctx.audioWorklet.addModule(URL.createObjectURL(new Blob([CAPTURE_WORKLET], { type: 'application/javascript' })));
  const mic = ctx.createMediaStreamSource(new MediaStream(stream.getAudioTracks()));
  const capture = new AudioWorkletNode(ctx, 'pcm16-capture');
  const mime = `audio/pcm;rate=${ctx.sampleRate}`;
  capture.port.onmessage = (e) => {
    if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ realtimeInput: { audio: { data: toBase64(e.data), mimeType: mime } } }));
  };
  mic.connect(capture);

  // the interviewer speaks first
  ws.send(JSON.stringify({ clientContent: { turns: [{ role: 'user', parts: [{ text: "Hi, I'm ready to start." }] }], turnComplete: true } }));
  onStatus?.('live');

  return {
    clock,
    stop() {
      closed = true;
      finishTurn(true);
      mic.disconnect();
      capture.port.onmessage = null;
      sources.forEach((s) => { try { s.stop(); } catch { /* already stopped */ } });
      ws.close();
      ctx.close();
      return turns;
    },
  };
}
