"""What the live interviewer does after each answer: ask a follow-up about what is missing, or move to the next question.

The interviewer used to ask exactly one follow-up after every answer. Now a text model reads the answer and says which of
three things it lacks: what the candidate did themselves, a number for the result, or a concrete example. Missing one of
them means a follow-up about that one; missing none means the next question. At most MAX_FOLLOWUPS per main question,
enforced here and not left to the model.

Why a tool and not a nudge from the side: the Live interviewer starts speaking 0.4 to 0.8 s after it decides an answer is
over (it answered 2.9 to 3.3 s after an answer ended, with 2.5 s of silence needed to end a turn). A decision sent from the
backend would have to fit a browser round trip and a model call into that gap, and would arrive while the interviewer is
already talking. As a tool, the interviewer asks for the decision and waits for it. The cost is that the decision time is
added to the pause the candidate hears, so it has a timeout: past FOLLOWUP_TIMEOUT_S the old rule applies (one follow-up
per question) and the timeout is recorded, so how often it happens can be counted.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

from . import config, store

# The order they are asked about. A general answer ("I usually...") has no situation to ask about yet, so the specific
# example comes first, then what the candidate did in it, then the result.
MISSING = ("example", "own_action", "result_number")
ASK = {  # used when the model names what is missing but gives no usable question
    "own_action": "You said the team did that. What did you do yourself?",
    "result_number": "What changed because of it? Is there a number you can put on the result?",
    "example": "Can you walk me through one specific time that happened?",
}

PROMPT = """FOLLOWUP_DECISION
You help a mock interviewer decide what to do after the candidate's answer. Judge only the answer below.

Main question: {question}
Follow-ups already asked on this question: {asked}
Everything the candidate said since the main question:
\"\"\"{answer}\"\"\"

Check three things. Each one is missing only if the answer gives no sign of it at all.
- example: one specific situation (a particular project, day, person or event). Missing if the answer stays general
  ("I always...", "usually...", "I'm the kind of person who...").
- own_action: what the candidate did themselves. Missing if they only say "we" or "the team", or describe what happened
  without saying what they did.
- result_number: a result with a number (a percentage, a count, time saved, money, a ranking, a before and after).
  Missing if the result is only described in words ("it went well", "it improved a lot") or there is no result.

Return JSON only: {{"missing": [zero or more of "example", "own_action", "result_number"], "ask": "one short follow-up
question about the FIRST missing item in that order, quoting two to six of the candidate's own words; empty if nothing is missing"}}"""

_pool = ThreadPoolExecutor(max_workers=8)


def _words(text):
    return len((text or "").split())


def parse(raw):
    """The model's JSON, reduced to (missing items in asking order, the suggested question). Bad output reads as
    'nothing missing', so a broken reply moves the interview on rather than asking a strange question."""
    try:
        data = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except ValueError:
        return [], ""
    said = data.get("missing") if isinstance(data, dict) else None
    missing = [m for m in MISSING if isinstance(said, list) and m in said]
    ask = data.get("ask") if isinstance(data, dict) and isinstance(data.get("ask"), str) else ""
    return missing, ask.strip()[:240]


def model_decision(call, question, answer, asked):
    """(missing, ask) from the text model. `call` is backend.with_client."""
    prompt = PROMPT.format(question=(question or "").strip()[:600] or "(not given)", asked=asked,
                           answer=(answer or "").strip()[:4000] or "(nothing)")
    raw, _ = call(lambda c, m: c.models.generate_content(
        model=m, contents=prompt,
        config={"response_mime_type": "application/json", "temperature": 0, **config.thinking(m, "followup")}).text)
    return parse(raw)


def fallback(asked, source):
    """The rule from before: one follow-up per main question, without saying what about."""
    if asked >= 1:
        return {"action": "next", "missing": None, "ask": "", "source": source}
    return {"action": "follow_up", "missing": None, "ask": "", "source": source}


def decide(call, question, answer, asked, timeout=None, who=(None, None), decider=None, source="model"):
    """{'action': 'follow_up' | 'next', 'missing', 'ask', 'source', 'ms'}.

    source: 'model' (the model decided), 'cap' (MAX_FOLLOWUPS reached, no model call), 'timeout_fallback' or
    'error_fallback' (the old one-follow-up rule). Every decision is recorded, without the answer text.
    `decider` replaces the model, for tests and for the rules baseline in eval/run_followup_eval.py."""
    asked = max(0, int(asked or 0))
    t0 = time.time()
    if asked >= config.MAX_FOLLOWUPS:
        out = {"action": "next", "missing": None, "ask": "", "source": "cap"}
    else:
        job = _pool.submit(decider or model_decision, call, question, answer, asked)
        try:
            said, ask = job.result(timeout=config.FOLLOWUP_TIMEOUT_S if timeout is None else timeout)
            missing = [m for m in MISSING if m in (said or [])]  # asking order is fixed here, whatever decided
            out = ({"action": "follow_up", "missing": missing[0], "ask": ask or ASK[missing[0]], "source": "model"}
                   if missing else {"action": "next", "missing": None, "ask": "", "source": "model"})
        except FutureTimeout:
            out = fallback(asked, "timeout_fallback")  # the model call keeps running in its thread; its answer is dropped
        except Exception:
            out = fallback(asked, "error_fallback")
    out["ms"] = int((time.time() - t0) * 1000)
    store.log_decision(who[0], who[1], asked, _words(answer), out)
    return out
