"""Accounts, and the rule that decides when a practice needs one.

The first practice is free and anonymous. After a visitor has finished one, the next practice needs an account
(email and password). The anonymous practice is tied to the account when it is made, so the history stays in one place.

Sign-in uses a signed token the browser sends as `Authorization: Bearer`, because the frontend and the backend
will live on different domains and cookies across them are fragile. The signing key is MAESTRO_SECRET, or a
random key kept in data/secret_key so tokens survive a restart. Passwords are stored only as salted hashes.
Swapping this for Google sign-in later changes `signup` and `login` and nothing else.
"""
import os
import re
import secrets
import uuid
from datetime import datetime

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from . import store

TOKEN_MAX_AGE_S = 30 * 24 * 3600
MIN_PASSWORD = 8
MAX_PASSWORD = 128  # hashing a megabyte password is a cheap way to tie a server up
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")
VISITOR = re.compile(r"^[A-Za-z0-9-]{16,64}$")

# What the free practice costs the visitor, said once so the UI and the API agree.
LOGIN_REQUIRED = "You have used your free practice. Create a free account to keep practicing, it takes a few seconds."


class AccountError(Exception):
    """Something the person can fix. `reason` is a stable word for the UI; the message is shown as written."""

    def __init__(self, message, reason):
        super().__init__(message)
        self.reason = reason


def secret_key():
    env = os.environ.get("MAESTRO_SECRET")
    if env:
        return env
    path = store.DATA_DIR / "secret_key"
    if not path.exists():
        store.DATA_DIR.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_hex(32))
    return path.read_text().strip()


def _signer():
    return URLSafeTimedSerializer(secret_key(), salt="maestro-auth")


def make_token(user_id):
    return _signer().dumps({"u": user_id})


def user_from_token(token):
    """The user id a token was issued to, or None when it is missing, forged or expired."""
    if not token:
        return None
    try:
        return _signer().loads(token, max_age=TOKEN_MAX_AGE_S).get("u")
    except (BadSignature, SignatureExpired):
        return None


def clean_visitor(value):
    return value if value and VISITOR.match(value) else None


def _check(email, password):
    email = (email or "").strip().lower()
    if not EMAIL.match(email):
        raise AccountError("That does not look like an email address.", "bad_email")
    if not (MIN_PASSWORD <= len(password or "") <= MAX_PASSWORD):
        raise AccountError(f"Use a password of at least {MIN_PASSWORD} characters.", "bad_password")
    return email


def claim(visitor_id, user_id):
    """Attach what this browser did before signing in to the account, so the first practice counts as theirs."""
    if not visitor_id:
        return
    with store._connect() as db:
        db.execute("UPDATE runs SET user_id = ? WHERE visitor_id = ? AND user_id IS NULL", (user_id, visitor_id))
        db.execute("UPDATE events SET user_id = ? WHERE visitor_id = ? AND user_id IS NULL", (user_id, visitor_id))


def signup(email, password, visitor_id=None):
    """Make an account. Returns {'token', 'email'}."""
    email = _check(email, password)
    user_id = uuid.uuid4().hex
    try:
        with store._connect() as db:
            db.execute("INSERT INTO users (id, email, password_hash, created_at) VALUES (?,?,?,?)",
                       (user_id, email, generate_password_hash(password), datetime.now().isoformat(timespec="seconds")))
    except store.sqlite3.IntegrityError:
        raise AccountError("There is already an account with that email. Sign in instead.", "email_taken")
    claim(visitor_id, user_id)
    return {"token": make_token(user_id), "email": email}


def login(email, password, visitor_id=None):
    email = (email or "").strip().lower()
    with store._connect() as db:
        row = db.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    # The same answer for an unknown email and a wrong password, so the form does not reveal who has an account.
    if not row or not check_password_hash(row[1], password or ""):
        raise AccountError("That email and password do not match.", "bad_login")
    claim(visitor_id, row[0])
    return {"token": make_token(row[0]), "email": email}


def email_of(user_id):
    with store._connect() as db:
        row = db.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()
    return row[0] if row else None


def needs_login(visitor_id, user_id):
    """True when this person has finished a practice and is not signed in. The first practice is free."""
    if user_id:
        return False
    return store.completed_runs(visitor_id=visitor_id) >= 1
