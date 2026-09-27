const r3 = (x) => Math.round(x * 1000) / 1000;

function median(arr) {
  const s = [...arr].sort((a, b) => a - b);
  const m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

function spans(flags, samples, minLen, extra) {
  const events = [];
  let start = -1;
  for (let i = 0; i <= samples.length; i++) {
    const active = i < samples.length && flags(samples[i]);
    if (active && start < 0) start = i;
    if (!active && start >= 0) {
      const s = samples[start].t;
      const e = samples[i - 1].end;
      if (e - s >= minLen) events.push({ start: r3(s), end: r3(e), duration: r3(e - s), ...extra(start, i) });
      start = -1;
    }
  }
  return events;
}

export function aggregateSignals(samples, opts = {}) {
  const { lookAwayMinS = 2.0, smileThreshold = 0.5, smileMinS = 0.3 } = opts;
  if (samples.length === 0) {
    return {
      duration_s: 0, face_present_ratio: 0, eye_contact_ratio: 0,
      look_away_events: [], smile_events: [], motion_mean: 0, motion_p90: 0,
    };
  }

  const dts = samples.slice(1).map((s, i) => s.t - samples[i].t);
  const lastDt = dts.length ? median(dts) : 0;
  const enriched = samples.map((s, i) => ({
    ...s,
    dt: i < dts.length ? dts[i] : lastDt,
    end: s.t + (i < dts.length ? dts[i] : lastDt),
  }));

  const duration = enriched.reduce((a, s) => a + s.dt, 0);
  if (duration === 0) {
    return { duration_s: 0, face_present_ratio: 0, eye_contact_ratio: 0, look_away_events: [], smile_events: [], motion_mean: 0, motion_p90: 0 };
  }
  const faceTime = enriched.reduce((a, s) => a + (s.face ? s.dt : 0), 0);
  const eyeTime = enriched.reduce((a, s) => a + (s.face && s.gaze ? s.dt : 0), 0);

  const look_away_events = spans((s) => !s.face || !s.gaze, enriched, lookAwayMinS, () => ({}));
  const smile_events = spans((s) => s.smile >= smileThreshold, enriched, smileMinS,
    (a, b) => ({ peak: r3(Math.max(...enriched.slice(a, b).map((s) => s.smile))) }));

  let motionMean = 0;
  for (const s of enriched) motionMean += s.motion * s.dt;

  const sorted = enriched.map((s) => s.motion).sort((a, b) => a - b);
  const p90 = sorted[Math.min(sorted.length - 1, Math.ceil(sorted.length * 0.9) - 1)];

  return {
    duration_s: r3(duration),
    face_present_ratio: r3(faceTime / duration),
    eye_contact_ratio: r3(faceTime ? eyeTime / faceTime : 0),
    look_away_events,
    smile_events,
    motion_mean: r3(motionMean / duration),
    motion_p90: r3(p90),
  };
}
