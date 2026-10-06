"""Audio metrics via ffmpeg/ffprobe: duration, pauses, and noise levels."""
import array
import math
import os
import re
import subprocess
import tempfile
import wave


def analyze_audio(path, min_pause_s=1.5, silence_db=-35.0, snr_threshold_db=15.0):
    """Return duration, speech time, non-edge pauses, and SNR stats for an audio file."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", path, "-ar", "16000", "-ac", "1",
             "-sample_fmt", "s16", tmp.name, "-nostats", "-loglevel", "error"],
            check=True, capture_output=True)
        dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", tmp.name],
            check=True, capture_output=True, text=True).stdout.strip())
        proc = subprocess.run(
            ["ffmpeg", "-i", tmp.name, "-af",
             f"silencedetect=noise={silence_db}dB:d={min_pause_s}",
             "-f", "null", "-"],
            capture_output=True, text=True)
        err = proc.stderr
        starts = [float(m) for m in re.findall(r"silence_start: ([\d.]+)", err)]
        ends = [float(m) for m in re.findall(r"silence_end: ([\d.]+)", err)]
        if len(ends) < len(starts):
            ends.append(dur)
        silences = [(s, e) for s, e in zip(starts, ends)]
        total_silence = sum(e - s for s, e in silences)
        pauses = [
            {"start": round(s, 2), "end": round(e, 2), "duration": round(e - s, 2)}
            for s, e in silences
            if s > 0.05 and e < dur - 0.05
        ]
        frames = _frame_dbfs(tmp.name)
        noise_db = _pct(frames, 10)
        speech_db = _pct(frames, 90)
        snr_db = speech_db - noise_db
        return {
            "duration_s": round(dur, 2),
            "speech_s": round(dur - total_silence, 2),
            "pauses": pauses,
            "long_pause_count": len(pauses),
            "noise_db": round(noise_db, 2),
            "speech_db": round(speech_db, 2),
            "snr_db": round(snr_db, 2),
            "noisy": snr_db < snr_threshold_db,
        }
    finally:
        os.unlink(tmp.name)


def _frame_dbfs(path, frame_s=0.05):
    """Yield per-frame dBFS values (50 ms default) from a 16-bit mono wav."""
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        data = array.array("h", w.readframes(n))
    per = int(16000 * frame_s)
    out = []
    for i in range(0, len(data), per):
        chunk = data[i:i + per]
        if not chunk:
            break
        rms = math.sqrt(sum(x * x for x in chunk) / len(chunk))
        out.append(-100.0 if rms == 0 else 20 * math.log10(rms / 32768.0))
    return out


def _pct(values, p):
    """Percentile of a list (simple sorted-index method)."""
    s = sorted(values)
    return s[min(len(s) - 1, int(len(s) * p / 100))]
