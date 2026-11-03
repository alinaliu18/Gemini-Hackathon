"""After a report: suggest the next practice on the weakest part, and only when the person agrees, make a calendar
invite whose link opens a practice that starts on that part.

The weakest part is worked out here from the saved report, never taken from the browser, so a plan always matches a
real report. Only dimensions that were scored count; "not measured" is not weak.
"""
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

from . import store

FOCUS = {  # dimension -> (what to call it, what the first question should make the candidate practice)
    "content": ("Substance", "giving a specific, relevant example with what you did and what came of it"),
    "structure": ("Structure", "telling it in order: the situation in one sentence, what you did, then the result"),
    "clarity": ("Clarity", "saying the main point in the first sentence, in plain words"),
    "pacing": ("Pace", "keeping a steady pace, with short pauses between points instead of long ones"),
    "filler_words": ("Filler words", "replacing um, like and you know with a short silent pause"),
    "eye_contact": ("Eye contact", "looking at the camera while making your main point"),
    "presence": ("Presence", "sitting centered in frame and keeping your energy up to the last sentence"),
}
LENGTH_MIN = 15


def weakest(report):
    """(dimension, score) with the lowest score in the report's summary, or in the per-answer feedback when there is
    no summary (a one-question practice). None when nothing was scored."""
    report = report or {}
    dims = (report.get("summary") or {}).get("dimensions") if isinstance(report.get("summary"), dict) else None
    if not dims:
        dims = report.get("dimensions") or {}
    if not dims and report.get("answers"):
        scores = {}
        for a in report["answers"]:
            for k, d in (a.get("dimensions") or {}).items():
                if isinstance(d, dict) and isinstance(d.get("score"), (int, float)):
                    scores.setdefault(k, []).append(d["score"])
        dims = {k: {"score": sum(v) / len(v)} for k, v in scores.items()}
    scored = [(k, d["score"]) for k, d in dims.items()
              if k in FOCUS and isinstance(d, dict) and isinstance(d.get("score"), (int, float))]
    return min(scored, key=lambda kv: kv[1]) if scored else None


def suggestion(report):
    w = weakest(report)
    if not w:
        return None
    label, how = FOCUS[w[0]]
    return {"dimension": w[0], "label": label, "how": how, "score": round(w[1])}


def app_url():
    return (os.environ.get("PUBLIC_APP_URL") or "http://localhost:5173").rstrip("/")


def _ics_time(dt):
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _ics_text(s):
    return s.replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace("\n", "\\n")


def ics(plan_id, label, how, starts_at, link):
    end = starts_at + timedelta(minutes=LENGTH_MIN)
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Interview Maestro//Next practice//EN", "METHOD:PUBLISH",
             "BEGIN:VEVENT", f"UID:{plan_id}@interview-maestro", f"DTSTAMP:{_ics_time(datetime.now(timezone.utc))}",
             f"DTSTART:{_ics_time(starts_at)}", f"DTEND:{_ics_time(end)}",
             f"SUMMARY:{_ics_text(f'Interview practice: {label}')}",
             f"DESCRIPTION:{_ics_text(f'The first question will focus on {how}. Open: {link}')}",
             f"URL:{link}", "BEGIN:VALARM", "TRIGGER:-PT10M", "ACTION:DISPLAY",
             f"DESCRIPTION:{_ics_text('Interview practice in 10 minutes')}", "END:VALARM", "END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(lines) + "\r\n"


class PlanError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def accept(run_id, starts_at, who):
    """The person agreed to the suggested practice. Returns {plan_id, link, ics, label, how, starts_at}."""
    row = store.get_run(run_id)
    if not row or row["status"] != "ok":
        raise PlanError("That report could not be found.", 404)
    owner = (row["user_id"] and row["user_id"] == who[1]) or (row["visitor_id"] and row["visitor_id"] == who[0])
    if (row["user_id"] or row["visitor_id"]) and not owner:
        raise PlanError("That report belongs to someone else.", 403)
    s = suggestion(json.loads(row["report_json"] or "{}"))
    if not s:
        raise PlanError("That report has nothing scored to practice next.")
    try:
        when = datetime.fromisoformat(starts_at) if starts_at else datetime.now(timezone.utc) + timedelta(days=1)
    except (TypeError, ValueError):
        raise PlanError("That time could not be read.")
    if when.tzinfo is None:
        raise PlanError("The time needs a time zone.")
    plan_id = uuid.uuid4().hex[:12]
    link = f"{app_url()}/?plan={plan_id}"
    store.save_plan(plan_id, run_id, who, s["dimension"], when.isoformat())
    return {"plan_id": plan_id, "link": link, "ics": ics(plan_id, s["label"], s["how"], when, link),
            "label": s["label"], "how": s["how"], "starts_at": when.isoformat()}


def get(plan_id):
    """What a plan link opens with: {dimension, label, how}, or None."""
    row = store.get_plan(plan_id)
    if not row or row["dimension"] not in FOCUS:
        return None
    label, how = FOCUS[row["dimension"]]
    return {"plan_id": plan_id, "dimension": row["dimension"], "label": label, "how": how}


def first_question_line(plan):
    """Added to the interviewer's instructions when the practice was opened from a plan link."""
    if not plan:
        return ""
    return (f"This practice was planned to work on {plan['label'].lower()}. Before your first question, say in one sentence "
            f"that today starts with {plan['label'].lower()}. Your FIRST main question must give the candidate a direct "
            f"chance to practice {plan['how']}.")
