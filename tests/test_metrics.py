"""Self-check for pipeline.audio_metrics and pipeline.text_metrics (plain asserts)."""
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.audio_metrics import analyze_audio
from pipeline.text_metrics import analyze_text

tmp = tempfile.mkdtemp()
clean = os.path.join(tmp, "clean.wav")
noisy = os.path.join(tmp, "noisy.wav")

subprocess.run(
    ["ffmpeg", "-y",
     "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
     "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=3",
     "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
     "-filter_complex", "[0][1][2]concat=n=3:v=0:a=1,volume=0.5",
     clean],
    check=True, capture_output=True)

subprocess.run(
    ["ffmpeg", "-y",
     "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
     "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono:d=3",
     "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
     "-f", "lavfi", "-i", "anoisesrc=color=white:amplitude=0.3:duration=7",
     "-filter_complex",
     "[0][1][2]concat=n=3:v=0:a=1,volume=0.5[s];[s][3]amix=inputs=2:duration=longest",
     noisy],
    check=True, capture_output=True)

c = analyze_audio(clean)
print("clean:", c)
pauses = c["pauses"]
assert len(pauses) == 1, pauses
assert abs(pauses[0]["duration"] - 3.0) <= 0.3, pauses
assert c["long_pause_count"] == 1
assert c["noisy"] is False, c

n = analyze_audio(noisy)
print("noisy:", n)
assert n["noisy"] is True, n
assert n["snr_db"] < c["snr_db"], (n["snr_db"], c["snr_db"])

segments = [
    {"start": 0, "end": 10,
     "text": "Um so I led the project, you know, and like, we shipped it. I like cats."},
    {"start": 10, "end": 20, "text": "嗯 then uh we measured it"},
]
t = analyze_text(segments, speech_s=20)
print("text:", t)
assert t["filler_breakdown"] == {"um": 1, "you know": 1, "like": 1, "嗯": 1, "uh": 1}, t["filler_breakdown"]
assert t["filler_count"] == 5
expected_wc = len(re.findall(r"[A-Za-z']+|[一-鿿]",
                             " ".join(s["text"] for s in segments)))
assert t["word_count"] == expected_wc, (t["word_count"], expected_wc)

from pipeline.transcribe import to_seconds
assert to_seconds("00:45") == 45 and to_seconds("01:07") == 67 and to_seconds("1:02:03") == 3723
assert to_seconds("00:04.5") == 4.5 and to_seconds(12.3) == 12.3

print("ALL OK")
