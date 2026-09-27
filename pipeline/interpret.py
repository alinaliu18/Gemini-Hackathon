"""Turn measured signals + transcript into feedback where every claim carries evidence.

Principles:
- What can be measured (pace, pauses, fillers, eye contact) is scored in code, not guessed by the model.
- Report observable behaviour only; never infer emotions ("nervous", "not confident").
- Every feedback item must cite a timestamp plus a verbatim quote or a signal value; unverifiable items are dropped.
"""
import json
import re

from . import config

EMOTION_WORDS = re.compile(
    r"\b(nervous|anxious|anxiety|not confident|lack(?:s|ed)? (?:of )?confidence|insecure|scared|afraid|"
    r"stressed|uncomfortable|panick?(?:ed|ing)?)\b|紧张|不自信|焦虑|害怕", re.I)


def mmss(t):
    t = max(0, int(round(float(t))))
    return f"{t // 60}:{t % 60:02d}"


def _norm(s):
    return re.sub(r"[^\w一-鿿]+", " ", s.lower()).strip()


# ---------- scored in code ----------
def score_pacing(text_m, audio_m, goal):
    if not audio_m["duration_s"]:
        return {"score": None, "observation": "No audio recorded.", "evidence": []}
    lo, hi = config.WPM_BANDS.get(goal, config.WPM_BANDS["default"])
    wpm = text_m["wpm"]
    off = max(0, lo - wpm, wpm - hi)
    noisy = audio_m.get("noisy")
    long_pauses = [] if noisy else [p for p in audio_m["pauses"] if p["duration"] >= config.LONG_PAUSE_S]
    score = max(40, 90 - off - 5 * max(0, len(long_pauses) - 1))
    band = "within" if off == 0 else ("above" if wpm > hi else "below")
    obs = f"Overall pace {wpm:.0f} words/min ({band} the {lo}-{hi} range for this track)."
    ev = [{"t": mmss(s["start"]), "signal": f"segment pace {s['wpm']:.0f} wpm"}
          for s in text_m["segment_wpm"] if not lo <= s["wpm"] <= hi][:3]
    if long_pauses:
        obs += f" {len(long_pauses)} pause(s) of {config.LONG_PAUSE_S:.0f}s or longer."
        ev += [{"t": mmss(p["start"]), "signal": f"pause {p['duration']:.1f}s"} for p in long_pauses[:3]]
    if noisy:
        obs += " Pauses not measured: background noise hides silences, so pace is estimated from transcript timestamps."
    if not ev:
        ev = [{"t": "0:00", "signal": f"overall pace {wpm:.0f} wpm"}]
    return {"score": int(score), "observation": obs, "evidence": ev}


def score_fillers(text_m, has_audio=True):
    if not has_audio:
        return {"score": None, "observation": "No audio recorded.", "evidence": []}
    fpm = text_m["fillers_per_min"]
    score = 90 if fpm <= 2 else 75 if fpm <= 4 else 60 if fpm <= 6 else 45
    top = ", ".join(f'"{k}" x{v}' for k, v in sorted(text_m["filler_breakdown"].items(), key=lambda kv: -kv[1])[:3])
    obs = f"{text_m['filler_count']} filler words ({fpm:.1f}/min)" + (f": {top}." if top else ".")
    ev = [{"t": mmss(e["t"]), "signal": f'filler "{e["term"]}"'} for e in text_m["filler_events"][:4]] \
        or [{"t": "0:00", "signal": "0 filler words"}]
    return {"score": score, "observation": obs, "evidence": ev}


def score_eye_contact(video):
    if not video:
        return {"score": None, "observation": "No video signals (camera off).", "evidence": []}
    r = video["eye_contact_ratio"]
    score = 90 if r >= .7 else 75 if r >= .5 else 60 if r >= .3 else 45
    obs = f"Looking toward the camera {r:.0%} of the time the face was visible."
    ev = [{"t": mmss(e["start"]), "signal": f"looked away {e['duration']:.1f}s"} for e in video["look_away_events"][:3]] \
        or [{"t": "0:00", "signal": f"eye contact {r:.0%}"}]
    return {"score": score, "observation": obs, "evidence": ev}


# ---------- interpreted by the model ----------
PROMPT = """You are an interview coach. You are given MEASURED FACTS about one recorded answer. Write feedback.

HARD RULES
1. Describe observable behaviour only. NEVER infer emotions or inner states (no "nervous", "anxious", "not confident").
   Say "3 pauses over 3s around 0:42" instead of "you seemed nervous".
2. Every item needs evidence: a timestamp "m:ss" plus either an EXACT quote copied from the transcript or a signal from the facts.
3. Smiling/laughing is a warmth/rapport cue. Never count it against the candidate. Mention it only as context.
4. Do not estimate pace, pauses or filler words yourself; those are already measured. Focus on what the words say.
5. If CLARITY_SCORABLE is false, set clarity to null (the recording is too noisy to judge articulation).
6. If there are no VIDEO facts, set presence to null.
7. Strengths first, then improvements, each improvement with one concrete tip.

Return ONLY JSON:
{"dimensions": {
   "content":   {"score": 0-100, "observation": "...", "evidence": [{"t": "m:ss", "quote": "..."}]},
   "structure": {"score": 0-100, "observation": "does it follow Situation-Task-Action-Result?", "evidence": [...]},
   "clarity":   {"score": 0-100 or null, "observation": "...", "evidence": [...]},
   "presence":  {"score": 0-100 or null, "observation": "posture/motion/face framing from video signals", "evidence": [{"t": "m:ss", "signal": "..."}]}},
 "strengths":    [{"text": "...", "evidence": [...]}],
 "improvements": [{"text": "...", "tip": "...", "evidence": [...]}],
 "congruence":   [{"text": "moment where words and delivery point different ways, stated as observation", "evidence": [...]}]}
"""


def build_facts(question, goal, focus, resume, segments, audio_m, text_m, video, clarity_scorable):
    lines = [f"QUESTION: {question or '(not given)'}", f"TRACK: {goal}. {focus}",
             f"RESUME (may be empty): {resume[:3000]}", "TRANSCRIPT:"]
    lines += [f"[{mmss(s['start'])}] {s['text']}" for s in segments] or ["(no speech detected)"]
    lines.append(f"AUDIO: duration {audio_m['duration_s']}s, speech {audio_m['speech_s']}s, "
                 f"SNR {audio_m['snr_db']} dB, CLARITY_SCORABLE={str(clarity_scorable).lower()}")
    lines.append(f"PACE: {text_m['wpm']} wpm; pauses: " +
                 (", ".join(f"{mmss(p['start'])} {p['duration']}s" for p in audio_m["pauses"]) or "none"))
    lines.append(f"FILLERS: {text_m['filler_breakdown'] or 'none'}")
    if video:
        lines.append(f"VIDEO: face visible {video['face_present_ratio']:.0%}, eye contact {video['eye_contact_ratio']:.0%}, "
                     f"motion mean {video['motion_mean']}, p90 {video['motion_p90']}")
        lines.append("  look-away: " + (", ".join(f"{mmss(e['start'])} {e['duration']}s" for e in video["look_away_events"]) or "none"))
        lines.append("  smiles: " + (", ".join(mmss(e["start"]) for e in video["smile_events"]) or "none"))
    return "\n".join(lines)


def _valid_evidence(ev_list, transcript_norm):
    good = []
    for ev in ev_list or []:
        if not isinstance(ev, dict) or not ev.get("t"):
            continue
        if ev.get("quote"):
            if _norm(ev["quote"]) and _norm(ev["quote"]) in transcript_norm:
                good.append({"t": str(ev["t"]), "quote": ev["quote"]})
        elif ev.get("signal"):
            good.append({"t": str(ev["t"]), "signal": str(ev["signal"])})
    return good


def _clean_items(items, transcript_norm, dropped, key):
    out = []
    for it in items or []:
        text = f"{it.get('text', '')} {it.get('tip', '')}"
        ev = _valid_evidence(it.get("evidence"), transcript_norm)
        if EMOTION_WORDS.search(text):
            dropped.append({"where": key, "why": "emotion inference", "text": it.get("text", "")})
        elif not ev:
            dropped.append({"where": key, "why": "no verifiable evidence", "text": it.get("text", "")})
        else:
            out.append({**it, "evidence": ev})
    return out


def validate(model_out, segments, clarity_scorable, has_video):
    """Enforce the hard rules in code; return (clean_output, dropped_items)."""
    transcript_norm = _norm(" ".join(s["text"] for s in segments))
    dropped, dims = [], {}
    for name in ("content", "structure", "clarity", "presence"):
        d = (model_out.get("dimensions") or {}).get(name) or {}
        forced_null = (name == "clarity" and not clarity_scorable) or (name == "presence" and not has_video)
        ev = _valid_evidence(d.get("evidence"), transcript_norm)
        obs = str(d.get("observation") or "")
        if forced_null:
            why = "Recording too noisy to judge articulation; try a quieter room." if name == "clarity" else "No video signals (camera off)."
            dims[name] = {"score": None, "observation": why, "evidence": []}
        elif EMOTION_WORDS.search(obs) or not ev or d.get("score") is None:
            dropped.append({"where": name, "why": "emotion inference" if EMOTION_WORDS.search(obs) else "no verifiable evidence", "text": obs})
            dims[name] = {"score": None, "observation": "Not enough evidence to judge.", "evidence": []}
        else:
            dims[name] = {"score": max(0, min(100, int(d["score"]))), "observation": obs, "evidence": ev}
    return {
        "dimensions": dims,
        "strengths": _clean_items(model_out.get("strengths"), transcript_norm, dropped, "strengths"),
        "improvements": _clean_items(model_out.get("improvements"), transcript_norm, dropped, "improvements"),
        "congruence": _clean_items(model_out.get("congruence"), transcript_norm, dropped, "congruence"),
    }, dropped


def overall_score(dims, goal):
    w = config.TRACK_WEIGHTS.get(goal, config.TRACK_WEIGHTS["Career"])
    pairs = [(w[k], d["score"]) for k, d in dims.items() if d["score"] is not None and k in w]
    total = sum(x for x, _ in pairs)
    return int(round(sum(x * s for x, s in pairs) / total)) if total else None


def score_coverage(dims, goal):
    """Share of the track's rubric weight that could actually be measured (a noisy, camera-off answer covers less)."""
    w = config.TRACK_WEIGHTS.get(goal, config.TRACK_WEIGHTS["Career"])
    covered = sum(w[k] for k, d in dims.items() if d["score"] is not None and k in w)
    return round(covered / sum(w.values()), 2), sorted(k for k, d in dims.items() if d["score"] is None and k in w)


def interpret(client, model, question, goal, resume, segments, audio_m, text_m, video):
    """Full interpretation step: model call + rule enforcement + code-scored dimensions + overall score."""
    clarity_scorable = bool(audio_m["duration_s"]) and not audio_m["noisy"]
    focus = config.TRACK_FOCUS.get(goal, config.TRACK_FOCUS["Career"])
    facts = build_facts(question, goal, focus, resume, segments, audio_m, text_m, video, clarity_scorable)
    resp = client.models.generate_content(
        model=model, contents=[PROMPT, facts],
        config={"response_mime_type": "application/json", "temperature": 0.2})
    raw = json.loads(resp.text.replace("```json", "").replace("```", "").strip())
    clean, dropped = validate(raw if isinstance(raw, dict) else {}, segments, clarity_scorable, bool(video))
    clean["dimensions"].update({
        "pacing": score_pacing(text_m, audio_m, goal),
        "filler_words": score_fillers(text_m, bool(audio_m["duration_s"])),
        "eye_contact": score_eye_contact(video),
    })
    if not audio_m["duration_s"]:
        clean["dimensions"]["clarity"]["observation"] = "No audio recorded."
    clean["score"] = overall_score(clean["dimensions"], goal)
    clean["score_coverage"], clean["not_measured"] = score_coverage(clean["dimensions"], goal)
    clean["dropped"] = dropped
    return clean
