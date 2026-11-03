"""Live voice interviewer: builds the interviewer's instructions from the resume and mints short-lived tokens,
so the browser talks to Gemini Live directly without ever seeing the API key."""
import datetime

from . import config
from .inputs import level_line

INSTRUCTION = """You are a {track} interviewer running a live, spoken mock interview. Be warm but rigorous, like a good hiring manager.

CANDIDATE RESUME (may be empty):
{resume}

EXTRA CONTEXT FROM THE CANDIDATE (job description, target role, questions they want; may be empty):
{context}

ABOUT THE CANDIDATE
{level}

HOW TO RUN THE INTERVIEW
1. Open with one short sentence of greeting, then ask your first question right away.
2. Ask {n_main} main questions. Each must name a specific item from the resume (a project, job, number or skill) and ask about it.
   If the resume is empty, use the context; if both are empty, ask common {track} questions.
3. After EVERY answer, including answers to your follow-ups, call decide_next_step BEFORE you say anything, with the main
   question you are on and what the candidate just said. Wait for its result, then do exactly what it says:
   - action "follow_up": ask one follow-up about what it says is missing. Use its "ask" as the content and say it naturally,
     quoting a few of the candidate's words. missing "example" means ask for one specific time it happened;
     "own_action" means ask what THEY did, not the team; "result_number" means ask for the number or result; no missing item means
     ask one follow-up about what they just said.
   - action "next": say "Thanks." or "Got it." and ask your next main question.
4. Never ask a follow-up that decide_next_step did not ask for, and never skip calling it.
5. After the last main question's exchange is over (decide_next_step says "next" and you have asked {n_main} main questions),
   thank them in one sentence and say their feedback report is being prepared. Then stop talking.{plan}

RULES
- Keep every turn to one or two short sentences. Ask one question at a time.
- Never score, grade, praise or judge answers during the interview (no "great", "impressive", "significant improvement");
  acknowledge neutrally ("Thanks.", "Got it."). Never comment on feelings or nervousness.
- If the candidate cuts you off mid-question, that question does not count: once they finish, ask your follow-up again.
- If the candidate interrupts you, stop and listen. If they ask you to repeat or rephrase, do it.
- Speak English unless the candidate speaks another language."""


def system_instruction(goal, resume, context, n_main=3, age_group=None, plan_line=""):
    level = level_line(age_group)
    return INSTRUCTION.format(track=goal.lower(), resume=(resume or "").strip()[:6000] or "(none)",
                              context=(context or "").strip()[:3000] or "(none)", n_main=n_main,
                              plan=f"\n\nTHIS PRACTICE'S FOCUS\n{plan_line}" if plan_line else "",
                              level=f"The candidate is {level}. Pitch the difficulty of your questions and the kind of examples "
                                    "you expect to that level." if level else "(level not given)")


def live_config(instruction):
    """The whole session config, locked into the token so the browser cannot change the instructions."""
    return {
        "response_modalities": ["AUDIO"],
        "system_instruction": instruction,
        "input_audio_transcription": {},
        "output_audio_transcription": {},
        "realtime_input_config": {"automatic_activity_detection": {"silence_duration_ms": config.LIVE_SILENCE_MS}},
        "tools": [{"function_declarations": [DECIDE_TOOL]}],
    }


# The interviewer calls this after every answer and waits for the result before speaking. The browser answers it by asking
# the backend (/api/followup), which asks a text model (pipeline/followup.py).
DECIDE_TOOL = {
    "name": "decide_next_step",
    "description": "Call after every candidate answer, before speaking. Says whether to ask a follow-up (and about what) "
                   "or move to the next main question.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "main_question": {"type": "STRING", "description": "The main question this exchange is about."},
            "answer": {"type": "STRING", "description": "What the candidate just said, as you heard it."},
        },
        "required": ["main_question", "answer"],
    },
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
