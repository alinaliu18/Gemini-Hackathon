"""Real Live API check (costs API calls), through the real backend routes:
/api/live/token (synthetic resume PDF) -> Live session -> two spoken answers streamed as the candidate
-> interviewer questions and follow-ups printed with latencies -> /api/session_report on the whole session.

Run: ./.venv/bin/python tests/live_smoke.py [model] [silence_ms]
"""
import asyncio, io, json, pathlib, subprocess, sys, time, wave

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import backend  # loads .env, builds the Flask app
from google import genai
from pipeline import config

if len(sys.argv) > 1:
    config.LIVE_MODEL = sys.argv[1]
if len(sys.argv) > 2:
    config.LIVE_SILENCE_MS = int(sys.argv[2])
OUT = ROOT / 'eval' / 'data' / 'live_smoke'  # gitignored
RATE = 16000
CHUNK = RATE // 10  # 100 ms of 16-bit mono PCM
ANSWERS = ['answer.webm', 'answer2.webm']
api = backend.app.test_client()


def pcm_of(name):
    return subprocess.run(['ffmpeg', '-v', 'error', '-i', str(ROOT / 'tests/fixtures' / name),
                           '-f', 's16le', '-ac', '1', '-ar', str(RATE), '-'], capture_output=True, check=True).stdout


async def main():
    r = api.post('/api/live/token', data={'goal': 'career', 'context_text': 'Product manager internship',
                                          'file': (open(ROOT / 'tests/fixtures/resume.pdf', 'rb'), 'resume.pdf')})
    assert r.status_code == 200, r.get_data(as_text=True)
    token, model = r.get_json()['token'], r.get_json()['model']
    client = genai.Client(api_key=token, http_options={'api_version': 'v1alpha'})  # the browser does the same with the token

    turns, t0 = [], time.monotonic()
    now = lambda: round(time.monotonic() - t0, 2)
    session_pcm = bytearray()  # what the candidate's mic records: silence while the interviewer talks, then each answer
    latencies = []

    async with client.aio.live.connect(model=model, config={}) as session:  # config comes locked from the token
        finished = asyncio.Queue()

        async def receiver():  # the only reader of the session: one loop per interviewer turn
            while True:
                text, first_audio, interrupted = '', None, False
                async for msg in session.receive():  # ends at turn_complete
                    sc = msg.server_content
                    if msg.data and first_audio is None:
                        first_audio = now()
                    if not sc:
                        continue
                    if sc.output_transcription and sc.output_transcription.text:
                        text += sc.output_transcription.text
                    interrupted |= bool(sc.interrupted)
                turn = {'role': 'interviewer', 'start': first_audio, 'end': now(), 'text': text.strip(), 'interrupted': interrupted}
                turns.append(turn)
                await finished.put(turn)

        rx = asyncio.create_task(receiver())
        start = now()
        await session.send_client_content(turns={'role': 'user', 'parts': [{'text': "Hi, I'm ready to start."}]}, turn_complete=True)
        opening = await asyncio.wait_for(finished.get(), 30)
        latencies.append(('opening question', round(opening['start'] - start, 2)))
        print(f"[interviewer +{latencies[-1][1]}s] {opening['text']}")

        async def pad():  # silence after an answer so voice activity detection ends the turn
            while True:
                await session.send_realtime_input(audio={'data': b'\0\0' * CHUNK, 'mime_type': f'audio/pcm;rate={RATE}'})
                await asyncio.sleep(0.1)

        for name in ANSWERS:
            pcm = pcm_of(name)
            answer_start = now()
            session_pcm.extend(b'\0\0' * max(0, int(RATE * answer_start) - len(session_pcm) // 2))
            for i in range(0, len(pcm), CHUNK * 2):  # real-time pace
                await session.send_realtime_input(audio={'data': pcm[i:i + CHUNK * 2], 'mime_type': f'audio/pcm;rate={RATE}'})
                await asyncio.sleep(0.1)
            answer_end = now()
            session_pcm.extend(pcm)
            print(f'[candidate {answer_start}-{answer_end}s] <{name}>')
            padder = asyncio.create_task(pad())
            while True:
                turn = await asyncio.wait_for(finished.get(), 30)
                during = turn['start'] is not None and turn['start'] < answer_end
                tag = 'jumped into a pause, cut off' if during else f"+{round(turn['start'] - answer_end, 2)}s after answer"
                print(f"[interviewer {tag}] {turn['text']}")
                if not during and not turn['interrupted']:
                    latencies.append((f'after {name}', round(turn['start'] - answer_end, 2)))
                    break
            padder.cancel()
        rx.cancel()

    OUT.mkdir(parents=True, exist_ok=True)
    wav = io.BytesIO()
    with wave.open(wav, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(bytes(session_pcm))
    (OUT / 'session.wav').write_bytes(wav.getvalue())
    (OUT / 'turns.json').write_text(json.dumps(turns, indent=1))
    print(json.dumps({'model': model, 'silence_ms': config.LIVE_SILENCE_MS, 'latency_s': dict(latencies)}))
    return wav.getvalue(), turns


def report(wav_bytes, turns):
    t = time.time()
    r = api.post('/api/session_report', data={
        'goal': 'career', 'context_text': 'Product manager internship', 'turns': json.dumps(turns),
        'audio_response': (io.BytesIO(wav_bytes), 'session.wav', 'audio/wav'),
        'file': (open(ROOT / 'tests/fixtures/resume.pdf', 'rb'), 'resume.pdf'),
        'video_signals': json.dumps({"duration_s": 60, "face_present_ratio": 0.95, "eye_contact_ratio": 0.72,
                                     "look_away_events": [{"start": 14.0, "end": 16.5, "duration": 2.5}],
                                     "smile_events": [], "motion_mean": 0.01, "motion_p90": 0.02})})
    assert r.status_code == 200, r.get_data(as_text=True)[:500]
    d = r.get_json()
    (OUT / 'report.json').write_text(json.dumps(d, indent=1))
    s = d['summary']
    print(f"\nREPORT in {time.time() - t:.1f}s: overall {s['score']} (coverage {s['score_coverage']}), {len(d['answers'])} answers")
    for kind in ('strengths', 'improvements'):
        for it in s[kind]:
            print(f"  {kind[:-1]}: {it['text']} @ {[e['t'] for e in it['evidence']]}")
    for a in d['answers']:
        print(f"  Q@{a['asked_at']}s score {a['score']}: {a['question'][:90]}")
    assert d['answers'] and all(it['evidence'] for k in ('strengths', 'improvements') for it in s[k])


if __name__ == '__main__':
    report(*asyncio.run(main()))
