import assert from "node:assert";
import { aggregateSignals } from "./aggregate.js";

const seq = (n, f) => Array.from({ length: n }, (_, i) => f(i));
const base = (t, over = {}) => ({ t, face: true, gaze: true, smile: 0, motion: 0.1, ...over });
const at10Hz = (n, over) => seq(n, (i) => base(i / 10, typeof over === "function" ? over(i) : over));

// a) 10 s all face+gaze, smile 0, motion 0.1
{
  const r = aggregateSignals(at10Hz(100));
  assert.strictEqual(r.eye_contact_ratio, 1);
  assert.strictEqual(r.face_present_ratio, 1);
  assert.strictEqual(r.look_away_events.length, 0);
  assert.strictEqual(r.smile_events.length, 0);
  assert.strictEqual(r.motion_mean, 0.1);
  assert.strictEqual(r.duration_s, 10);
}

// b) gaze false t=3.0..5.9 (30 samples)
{
  const r = aggregateSignals(at10Hz(100, (i) => ({ gaze: !(i >= 30 && i <= 59) })));
  assert.strictEqual(r.look_away_events.length, 1);
  const ev = r.look_away_events[0];
  assert.ok(Math.abs(ev.duration - 3.0) <= 0.11, `duration ${ev.duration}`);
}

// c) gaze false only 1.0 s
{
  const r = aggregateSignals(at10Hz(100, (i) => ({ gaze: !(i >= 30 && i <= 39) })));
  assert.strictEqual(r.look_away_events.length, 0);
}

// d) face false 2.5 s
{
  const r = aggregateSignals(at10Hz(100, (i) => ({ face: i < 30 || i >= 55 })));
  assert.strictEqual(r.look_away_events.length, 1);
  assert.ok(Math.abs(r.look_away_events[0].duration - 2.5) <= 0.11);
}

// e) smile events
{
  const long = aggregateSignals(at10Hz(100, (i) => ({ smile: i >= 20 && i < 25 ? 0.8 : 0 })));
  assert.strictEqual(long.smile_events.length, 1);
  assert.strictEqual(long.smile_events[0].peak, 0.8);
  const short = aggregateSignals(at10Hz(100, (i) => ({ smile: i >= 20 && i < 22 ? 0.8 : 0 })));
  assert.strictEqual(short.smile_events.length, 0);
}

// f) empty
{
  const r = aggregateSignals([]);
  assert.strictEqual(r.duration_s, 0);
  assert.strictEqual(r.face_present_ratio, 0);
  assert.strictEqual(r.eye_contact_ratio, 0);
  assert.strictEqual(r.look_away_events.length, 0);
  assert.strictEqual(r.smile_events.length, 0);
  assert.strictEqual(r.motion_mean, 0);
  assert.strictEqual(r.motion_p90, 0);
}

{ const r = aggregateSignals([{ t: 0, face: true, gaze: true, smile: 0, motion: 0 }]); assert.equal(r.duration_s, 0); assert.equal(r.eye_contact_ratio, 0); }
console.log("ALL OK");
