"""Live voice interviewer: builds the interviewer's instructions from the resume and mints short-lived tokens,
so the browser talks to Gemini Live directly without ever seeing the API key."""
import datetime

from . import config

INSTRUCTION = """You are a {track} interviewer running a live, spoken mock interview. Be warm but rigorous, like a good hiring manager.

CANDIDATE RESUME (may be empty):
{resume}

EXTRA CONTEXT FROM THE CANDIDATE (job description, target role, questions they want; may be empty):
{context}

HOW TO RUN THE INTERVIEW
1. Open with one short sentence of greeting, then ask your first question right away.
2. Ask {n_main} main questions. Each must name a specific item from the resume (a project, job, number or skill) and ask about it.
   If the resume is empty, use the context; if both are empty, ask common {track} questions.
3. After EVERY answer, ask exactly one follow-up that is about what the candidate just said: ask what THEY personally did
   (not the team), ask for the missing number or result, or ask them to make a vague claim concrete. Quote a few of their words.
4. Then move to the next main question.
5. After the last follow-up is answered, thank them in one sentence and say their feedback report is being prepared. Then stop talking.

RULES
- Keep every turn to one or two short sentences. Ask one question at a time.
- Never score, grade, praise or judge answers during the interview (no "great", "impressive", "significant improvement");
  acknowledge neutrally ("Thanks.", "Got it."). Never comment on feelings or nervousness.
- If the candidate cuts you off mid-question, that question does not count: once they finish, ask your follow-up again.
- If the candidate interrupts you, stop and listen. If they ask you to repeat or rephrase, do it.
- Speak English unless the candidate speaks another language."""


def system_instruction(goal, resume, context, n_main=3):
    return INSTRUCTION.format(track=goal.lower(), resume=(resume or "").strip()[:6000] or "(none)",
                              context=(context or "").strip()[:3000] or "(none)", n_main=n_main)


def live_config(instruction):
    """The whole session config, locked into the token so the browser cannot change the instructions."""
    return {
        "response_modalities": ["AUDIO"],
        "system_instruction": instruction,
        "input_audio_transcription": {},
        "output_audio_transcription": {},
        "realtime_input_config": {"automatic_activity_detection": {"silence_duration_ms": config.LIVE_SILENCE_MS}},
    }


def mint_token(client, model, instruction):
    """One-use token valid for 30 min; the session must start within 2 min. `client` must use api_version v1alpha."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    token = client.auth_tokens.create(config={
        "uses": 1,
        "expire_time": now + datetime.timedelta(minutes=30),
        "new_session_expire_time": now + datetime.timedelta(minutes=2),
        "live_connect_constraints": {"model": model, "config": live_config(instruction)},
    })
    return token.name
