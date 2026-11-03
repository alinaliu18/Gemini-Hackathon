"""Daily limits per IP address and for the whole site. The site-wide limit is the real brake on the Gemini bill.

Counted when a practice starts: a live interview when its token is minted, a quick practice when it is scored, a
report when it is requested (so the report route cannot be used without a token to dodge the live limit).
The day rolls over at midnight Pacific time, where the students are. A failed start is given back.

An IP address is never stored. The counter keys on a keyed hash of it.

Behind Cloud Run the client address is in X-Forwarded-For, and the client can put anything it likes at the front of
that header. So the address is read from the right, skipping as many hops as TRUSTED_PROXY_HOPS says are ours
(1 on Cloud Run, 0 when running locally, which uses the connection's own address).
"""
import hashlib
import hmac
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from . import accounts, store

PACIFIC = ZoneInfo("America/Los_Angeles")

# kind -> (per IP per day, environment variable for the site-wide cap, its default). A site cap of 0 closes the site.
LIMITS = {
    "live": (5, "GLOBAL_DAILY_CAP", 50),
    "practice": (20, "GLOBAL_PRACTICE_CAP", 300),
    "report": (10, "GLOBAL_REPORT_CAP", 100),
    # Not practices. They stop the open doors (reading any web page, trying passwords, filling the events table).
    "jobpost": (30, "GLOBAL_JOBPOST_CAP", 1000),
    "auth": (60, "GLOBAL_AUTH_CAP", 2000),       # a campus shares a few addresses, so this is generous
    "event": (5000, "GLOBAL_EVENT_CAP", 200000),
    "followup": (400, "GLOBAL_FOLLOWUP_CAP", 10000),  # about 9 per interview, each one a text model call
}
PRACTICES = ("live", "practice", "report")

MESSAGES = {
    ("daily_limit", True): "You have reached today's limit for practice from this connection. It resets at midnight Pacific time.",
    ("busy", True): "Interview Maestro is at its daily capacity. Please try again tomorrow.",
    ("daily_limit", False): "Too many requests from this connection today. Please try again tomorrow.",
    ("busy", False): "Interview Maestro is busy right now. Please try again later.",
}


class LimitError(Exception):
    def __init__(self, reason, kind="live"):
        super().__init__(MESSAGES[(reason, kind in PRACTICES)])
        self.reason = reason


def today():
    return datetime.now(PACIFIC).strftime("%Y-%m-%d")


def client_ip(remote_addr, forwarded_for):
    hops = int(os.environ.get("TRUSTED_PROXY_HOPS", "0") or 0)
    if hops > 0 and forwarded_for:
        parts = [p.strip() for p in forwarded_for.split(",") if p.strip()]
        if len(parts) >= hops:
            return parts[-hops]
    return remote_addr or "unknown"


def _bucket(ip):
    return hmac.new(accounts.secret_key().encode(), ip.encode(), hashlib.sha256).hexdigest()[:20]


def _site_cap(kind):
    return int(os.environ.get(LIMITS[kind][1], LIMITS[kind][2]))


def take(kind, ip):
    """Count one use of `kind` for this IP and for the site. Raises LimitError when either limit is reached,
    counting nothing in that case."""
    per_ip = int(os.environ.get(f"IP_DAILY_{kind.upper()}", LIMITS[kind][0]))
    day, bucket = today(), _bucket(ip)
    db = store._connect()
    db.isolation_level = None  # explicit transaction, so two requests cannot both take the last slot
    try:
        db.execute("BEGIN IMMEDIATE")
        used = dict(db.execute("SELECT bucket, n FROM usage WHERE day = ? AND kind = ? AND bucket IN (?, 'site')",
                               (day, kind, bucket)).fetchall())
        if used.get("site", 0) >= _site_cap(kind):
            db.execute("ROLLBACK")
            raise LimitError("busy", kind)
        if used.get(bucket, 0) >= per_ip:
            db.execute("ROLLBACK")
            raise LimitError("daily_limit", kind)
        for b in (bucket, "site"):
            db.execute("INSERT INTO usage (day, bucket, kind, n) VALUES (?,?,?,1) "
                       "ON CONFLICT (day, bucket, kind) DO UPDATE SET n = n + 1", (day, b, kind))
        db.execute("COMMIT")
    finally:
        db.close()


def give_back(kind, ip):
    """Undo one `take`, for a practice that failed before it began."""
    day, bucket = today(), _bucket(ip)
    with store._connect() as db:
        db.execute("UPDATE usage SET n = MAX(n - 1, 0) WHERE day = ? AND kind = ? AND bucket IN (?, 'site')",
                   (day, kind, bucket))
