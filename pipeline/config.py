"""Tunable thresholds and weights. Initial values are assumptions: calibrate them against human-rated samples (eval/)."""

MODEL_ID = "gemini-2.5-flash"

# Audio
MIN_PAUSE_S = 1.5          # silence at least this long counts as a pause
LONG_PAUSE_S = 3.0         # pauses at least this long are surfaced as feedback
SILENCE_DB = -35.0         # ffmpeg silencedetect threshold
SNR_THRESHOLD_DB = 15.0    # below this the recording is "noisy": clarity is not scored

# Speaking rate bands (words per minute) per track: (too_slow_below, too_fast_above)
WPM_BANDS = {
    "Academic": (110, 160),
    "Career": (120, 170),
    "Social": (120, 180),
    "default": (120, 170),
}

# Video (browser MediaPipe signals)
LOOK_AWAY_MIN_S = 2.0

# Overall score = weighted mean of the dimensions that could be scored (null ones are skipped).
TRACK_WEIGHTS = {
    "Career":   {"content": .30, "structure": .20, "clarity": .15, "pacing": .10, "filler_words": .05, "eye_contact": .10, "presence": .10},
    "Academic": {"content": .30, "structure": .25, "clarity": .20, "pacing": .10, "filler_words": .05, "eye_contact": .05, "presence": .05},
    "Social":   {"content": .15, "structure": .10, "clarity": .15, "pacing": .15, "filler_words": .10, "eye_contact": .20, "presence": .15},
}

TRACK_FOCUS = {
    "Academic": "Focus on clarity of research explanation, logical structure, enthusiasm for the field.",
    "Social": "Focus on friendliness, conversational flow, ability to connect.",
    "Career": "Focus on professionalism, relevant experience, problem-solving.",
}
