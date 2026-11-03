"""The four numbers to watch after launch, and the events behind them.

  1. Success rate: of the practices that were started, how many ended with a report.
  2. Where people drop off: how many people reach each step, and what share of the step before.
  3. Return rate: of the people who saw a report, how many came back for a second practice.
  4. Score change: for people who practiced twice, how much the second score moved from the first.

Events hold a name, a time, who (a random browser id, and the account once there is one) and a few short facts such as
which kind of practice. They never hold what anyone said, the resume or the job description.

Print the numbers: ./.venv/bin/python -m pipeline.analytics [days]   (default 30)
"""
import json
import sys
from datetime import datetime, timedelta

from . import store

# The steps of the funnel, in order, with what each one means. The last two depend on features that may not exist yet:
# "next_session_agreed" is sent when someone accepts the suggested next practice, "second_practice_started" is worked
# out here from the other events and is never sent by the browser.
FUNNEL = [
    ("home_view", "Opened the home page"),
    ("resume_uploaded", "Added a resume"),
    ("job_description_filled", "Added a job description long enough to use"),
    ("interview_started", "Started an interview or a practice"),
    ("answer_finished", "Finished answering"),
    ("report_viewed", "Saw the report"),
    ("next_session_agreed", "Agreed to a suggested next practice"),
    ("second_practice_started", "Came back and started a second practice"),
]
OTHER_EVENTS = ("login_prompted", "account_created", "connection_lost", "report_from_partial")
SENT_BY_BROWSER = {name for name, _ in FUNNEL if name != "second_practice_started"} | set(OTHER_EVENTS)

ABANDONED_AFTER = timedelta(minutes=60)  # a run still "running" this long after it began is counted as not finished


def _clean_props(props):
    """Keep a few short plain facts. Anything long or nested is dropped, so free text cannot ride along."""
    out = {}
    for key, value in list((props or {}).items())[:8]:
        if isinstance(value, (bool, int, float)) or (isinstance(value, str) and len(value) <= 40):
            out[str(key)[:30]] = value
    return out


def record(name, visitor_id=None, user_id=None, props=None):
    if name not in SENT_BY_BROWSER:
        raise ValueError(f"unknown event {name!r}")
    with store._connect() as db:
        db.execute("INSERT INTO events (at, name, visitor_id, user_id, props_json) VALUES (?,?,?,?,?)",
                   (datetime.now().isoformat(timespec="seconds"), name, visitor_id, user_id, json.dumps(_clean_props(props))))


def _since(days, now):
    return (now - timedelta(days=days)).isoformat(timespec="seconds")


def compute(days=30, now=None):
    now = now or datetime.now()
    since = _since(days, now)
    with store._connect() as db:
        events = db.execute("SELECT at, name, COALESCE(user_id, visitor_id) FROM events WHERE at >= ? "
                            "AND COALESCE(user_id, visitor_id) IS NOT NULL ORDER BY at, id", (since,)).fetchall()
        runs = db.execute("SELECT created_at, kind, status, score, COALESCE(user_id, visitor_id) FROM runs "
                          "WHERE created_at >= ? ORDER BY created_at, rowid", (since,)).fetchall()

    # people at each step
    people = {name: set() for name, _ in FUNNEL}
    per_person = {}
    for at, name, who in events:
        per_person.setdefault(who, []).append((at, name))
        if name in people:
            people[name].add(who)
    for who, seq in per_person.items():  # a second start that comes after a report was seen
        seen_report = False
        starts = 0
        for _, name in seq:
            if name == "report_viewed":
                seen_report = True
            elif name == "interview_started":
                starts += 1
                if starts >= 2 and seen_report:
                    people["second_practice_started"].add(who)
                    break
    steps, previous = [], None
    for name, label in FUNNEL:
        n = len(people[name])
        steps.append({"name": name, "label": label, "people": n,
                      "share_of_previous": None if previous in (None, 0) else n / previous})
        previous = n

    # success rate
    cutoff = (now - ABANDONED_AFTER).isoformat(timespec="seconds")
    counted = [r for r in runs if not (r[2] == "running" and r[0] > cutoff)]
    succeeded = sum(1 for r in counted if r[2] == "ok")

    # score change between the first and the second practice of the same kind
    by_person_kind, deltas = {}, []
    for _, kind, status, score, who in runs:
        if status == "ok" and score is not None and who:
            by_person_kind.setdefault((who, kind), []).append(score)
    for scores in by_person_kind.values():
        if len(scores) >= 2:
            deltas.append(scores[1] - scores[0])

    first_done = len(people["report_viewed"])
    return {
        "days": days,
        "success": {"started": len(counted), "with_report": succeeded,
                    "rate": succeeded / len(counted) if counted else None},
        "steps": steps,
        "return": {"saw_report": first_done, "came_back": len(people["second_practice_started"]),
                   "rate": len(people["second_practice_started"]) / first_done if first_done else None,
                   "agreed": len(people["next_session_agreed"]),
                   "agreed_and_came_back": len(people["next_session_agreed"] & people["second_practice_started"])},
        "score_change": {"people": len(deltas), "average": sum(deltas) / len(deltas) if deltas else None,
                         "improved": sum(1 for d in deltas if d > 0)},
    }


def _pct(x):
    return "no data yet" if x is None else f"{x:.0%}"


def describe(m):
    s, r, c = m["success"], m["return"], m["score_change"]
    lines = [f"Last {m['days']} days", "",
             "1. Success rate",
             f"   {s['started']} practices were started and {s['with_report']} ended with a report: {_pct(s['rate'])}.", "",
             "2. Where people drop off (people who reached each step)"]
    for st in m["steps"]:
        share = "" if st["share_of_previous"] is None else f"  ({st['share_of_previous']:.0%} of the step above)"
        lines.append(f"   {st['people']:>5}  {st['label']}{share}")
    lines += ["", "3. Return rate",
              f"   {r['saw_report']} people saw a report and {r['came_back']} of them came back for a second practice: {_pct(r['rate'])}."]
    if r["agreed"]:
        lines.append(f"   {r['agreed']} agreed to a suggested next practice and {r['agreed_and_came_back']} of them came back.")
    lines += ["", "4. Score change from the first practice to the second"]
    if c["people"]:
        lines.append(f"   {c['people']} people practiced twice. Their score moved by {c['average']:+.1f} points on average "
                     f"(scores run from 0 to 100), and {c['improved']} of them improved.")
    else:
        lines.append("   Nobody has practiced twice yet.")
    return "\n".join(lines)


if __name__ == "__main__":
    print(describe(compute(int(sys.argv[1]) if len(sys.argv) > 1 else 30)))
