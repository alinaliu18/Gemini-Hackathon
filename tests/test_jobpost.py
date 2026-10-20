"""Offline check of reading a job posting from a URL: HTML to text, the schema.org shortcut, the addresses that
must be refused, and what the route answers. No network and no Gemini: the HTTP getter is faked.
Run: GEMINI_API_KEY=offline-placeholder ./.venv/bin/python tests/test_jobpost.py"""
import json, os, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["MAESTRO_DATA_DIR"] = tempfile.mkdtemp()
os.environ.setdefault("GEMINI_API_KEY", "offline-placeholder")
from pipeline import jobpost
from pipeline.jobpost import JobPostError

DESC = ("You will run user research with students, write the spec, and work with two engineers. "
        "Requirements: coursework in product or design, one shipped project, and clear writing. "
        "This is a paid internship for the winter quarter, based in Los Angeles, 20 hours a week.")


class Res:
    def __init__(self, status=200, text="", ctype="text/html; charset=utf-8", location=None):
        self.status_code, self.text = status, text
        self.headers = {"Content-Type": ctype} | ({"Location": location} if location else {})


def getter(*responses):
    """A fake requests.get that answers with the given responses in order and records the URLs it was given."""
    seen = []
    def get(url, **kw):
        seen.append(url)
        return responses[min(len(seen) - 1, len(responses) - 1)]
    get.seen = seen
    return get


# Fake name lookup, so the test needs no DNS. Anything not listed does not resolve.
import socket
HOSTS = {"boards.example.com": "93.184.216.34", "www.linkedin.com": "13.107.42.14",
         "127.0.0.1": "127.0.0.1", "169.254.169.254": "169.254.169.254", "10.0.0.5": "10.0.0.5",
         "192.168.1.1": "192.168.1.1", "::1": "::1"}

def resolve(host, port, **kw):
    if host not in HOSTS:
        raise socket.gaierror(-5, "no address")
    ip = HOSTS[host]
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, port))]


def fetch(url, get=None):
    return jobpost.fetch_job_text(url, get=get, resolve=resolve)


def fails(url, reason, get=None):
    try:
        fetch(url, get=get or getter(Res(200, "<p>x</p>")))
    except JobPostError as e:
        assert e.reason == reason, f"{url}: expected {reason}, got {e.reason}"
        assert str(e) and str(e)[0].isupper(), f"{url}: message must be readable, got {str(e)!r}"
        return
    raise AssertionError(f"{url}: expected {reason}, no error raised")


# 1) a plain page: nav, scripts and styles are dropped, blocks become line breaks
page = (f"<html><head><title>Product Manager Intern at Acme</title><style>p{{color:red}}</style>"
        f"<script>track()</script></head><body><nav>Jobs Login</nav><h1>Product Manager Intern</h1>"
        f"<p>{DESC}</p><ul><li>Ship features</li></ul><footer>Acme Inc 2026</footer></body></html>")
out = fetch("https://boards.example.com/jobs/7", get=getter(Res(200, page)))
assert "Product Manager Intern" in out["text"] and "run user research" in out["text"], out["text"]
assert "track()" not in out["text"] and "color:red" not in out["text"], "script or style text leaked in"
assert "Jobs Login" not in out["text"] and "Acme Inc 2026" not in out["text"], "nav or footer text leaked in"
assert "Ship features" in out["text"] and out["chars"] == len(out["text"]), out
assert "\n\n\n" not in out["text"], "blank lines not collapsed"

# 2) schema.org JobPosting is preferred: boards embed it for Google, and it is cleaner than the rendered page
ld = json.dumps({"@type": "JobPosting", "title": "PM Intern",
                 "hiringOrganization": {"name": "Acme"}, "description": f"<p>{DESC}</p>"})
mixed = (f'<html><body><script type="application/ld+json">{ld}</script>'
         f'<div>Cookie banner. Sign in to see this job. Apply on the company website.</div></body></html>')
out = fetch("https://www.linkedin.com/jobs/view/123", get=getter(Res(200, mixed)))
assert out["text"].startswith("PM Intern\nAcme"), out["text"]
assert "Cookie banner" not in out["text"], "the rendered page was used even though JobPosting was there"

# 3) addresses that must never be fetched: the backend will be public and takes this URL from the user
for bad in ["http://127.0.0.1:5002/api/health", "http://169.254.169.254/computeMetadata/v1/", "http://10.0.0.5/",
            "http://192.168.1.1/", "http://[::1]/"]:
    fails(bad, "blocked_host")
for bad in ["file:///etc/passwd", "not a url", "", "ftp://example.com/x", "https://nope.invalid/x"]:
    fails(bad, "bad_url")

# 4) a bare hostname is treated as https, the fragment is dropped
assert jobpost.safe_url("boards.example.com/jobs/7#apply", resolve) == "https://boards.example.com/jobs/7"

# 5) a login wall, an error page and a PDF link each say what to do instead
fails("https://www.linkedin.com/jobs/view/123", "fetch_failed", get=getter(Res(403, "Sign in")))
fails("https://boards.example.com/gone", "fetch_failed", get=getter(Res(404, "Not found")))
fails("https://boards.example.com/jd.pdf", "not_html", get=getter(Res(200, "%PDF-1.4", ctype="application/pdf")))

# 6) a page that is only a JavaScript shell is a failure, not an empty job description
fails("https://boards.example.com/spa", "too_short", get=getter(Res(200, '<html><body><div id="root"></div></body></html>')))

# 7) redirects are followed, and each hop is re-checked, so a redirect cannot reach a private address
g = getter(Res(302, location="https://boards.example.com/jobs/7-real"), Res(200, page))
assert fetch("https://boards.example.com/jobs/7", get=g)["url"].endswith("7-real")
assert len(g.seen) == 2, g.seen
fails("https://boards.example.com/jobs/7", "blocked_host",
      get=getter(Res(302, location="http://169.254.169.254/computeMetadata/v1/")))
fails("https://boards.example.com/loop", "fetch_failed",
      get=getter(Res(302, location="https://boards.example.com/loop")))

# 8) a long page is capped, so one posting cannot fill the prompt or the database
big = "<html><body>" + "<p>" + ("Responsibilities include shipping features. " * 2000) + "</p></body></html>"
assert len(fetch("https://boards.example.com/big", get=getter(Res(200, big)))["text"]) == jobpost.MAX_CHARS

# ---- the route and the required inputs ----
import backend
client = backend.app.test_client()

r = client.post("/api/job_post", data={"url": "not a url"})
assert r.status_code == 400 and r.get_json()["reason"] == "bad_url", r.get_json()

backend.jobpost.fetch_job_text = lambda url, get=None: {"url": url, "text": DESC, "chars": len(DESC), "source": url}
r = client.post("/api/job_post", data={"url": "https://boards.example.com/jobs/7"})
assert r.status_code == 200 and r.get_json()["text"] == DESC, r.get_json()

def boom(url, get=None):
    raise JobPostError("That site asks for a login before showing the posting.", "fetch_failed")
backend.jobpost.fetch_job_text = boom
r = client.post("/api/job_post", data={"url": "https://www.linkedin.com/jobs/view/123"})
assert r.status_code == 400 and r.get_json()["reason"] == "fetch_failed" and "login" in r.get_json()["error"], r.get_json()

# the live interview will not start without both inputs, so neither can be quietly missing
import io
pdf = io.BytesIO(b"%PDF-1.4 fake")
r = client.post("/api/live/token", data={"goal": "career", "context_text": DESC}, content_type="multipart/form-data")
assert r.status_code == 400 and r.get_json()["reason"] == "resume_required", r.get_json()
r = client.post("/api/live/token", data={"goal": "career", "context_text": "   ", "file": (pdf, "r.pdf")},
                content_type="multipart/form-data")
assert r.status_code == 400 and r.get_json()["reason"] == "job_required", r.get_json()

# a PDF that is a scan, or is not readable, must not be sent to the model as the resume text
backend.PyPDF2 = type("Fake", (), {"PdfReader": staticmethod(lambda f: (_ for _ in ()).throw(ValueError("damaged")))})
r = client.post("/api/live/token", data={"goal": "career", "context_text": DESC, "file": (io.BytesIO(b"x"), "r.pdf")},
                content_type="multipart/form-data")
assert r.status_code == 400 and r.get_json()["reason"] == "resume_unreadable", r.get_json()
backend.PyPDF2 = type("Empty", (), {"PdfReader": staticmethod(lambda f: type("R", (), {"pages": []})())})
r = client.post("/api/live/token", data={"goal": "career", "context_text": DESC, "file": (io.BytesIO(b"x"), "r.pdf")},
                content_type="multipart/form-data")
assert r.status_code == 400 and r.get_json()["reason"] == "resume_unreadable", r.get_json()

print("ALL OK")
