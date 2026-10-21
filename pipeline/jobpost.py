"""Read a job posting from a URL, so the candidate pastes a link instead of copying the whole page.

The fetch is deliberately narrow, because this route takes a URL from the public internet and the backend
will be deployed: http(s) only, public addresses only, redirects re-checked by hand, body size capped.

Many job boards answer a plain fetch with a login wall or an empty JavaScript shell. LinkedIn is the usual
case. So a result under MIN_CHARS is reported as a failure with a reason, and the UI asks for a paste
instead of silently sending a useless page to the interviewer.
"""
import ipaddress
import json
import re
import socket
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlparse, urlunparse

MIN_CHARS = 200          # under this the page is a login wall or a JS shell, not a posting
MAX_CHARS = 12_000       # what gets stored and put in the prompt; live.py trims the context again anyway
MAX_BYTES = 3_000_000    # stop reading a page bigger than this
MAX_REDIRECTS = 3
TIMEOUT_S = 10
UA = "InterviewMaestro/1.0 (job posting reader)"

# Tags whose text is never part of a posting.
DROP = {"script", "style", "noscript", "template", "svg", "head", "nav", "footer", "header", "form", "button", "select"}
BLOCK = {"p", "div", "li", "br", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "ul", "ol", "td"}


class JobPostError(Exception):
    """Something the user can act on. The message is shown in the UI as-is."""

    def __init__(self, message, reason):
        super().__init__(message)
        self.reason = reason  # 'bad_url' | 'blocked_host' | 'fetch_failed' | 'not_html' | 'too_short'


class _Text(HTMLParser):
    """Visible text only, with block tags turned into line breaks."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP:
            self.skip += 1
        elif tag in BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in DROP:
            self.skip = max(0, self.skip - 1)
        elif tag in BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

    def text(self):
        return "".join(self.parts)


def tidy(text):
    """Collapse runs of spaces and blank lines, so the prompt is not mostly whitespace."""
    text = unescape(text or "").replace("\r", "\n").replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def from_json_ld(html):
    """Job boards embed a schema.org JobPosting for Google so their listings get indexed. When it is there it
    is far cleaner than the rendered page, and LinkedIn's public job pages include it."""
    for raw in re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html,
                          re.S | re.I):
        try:
            data = json.loads(raw.strip())
        except ValueError:
            continue
        for node in (data if isinstance(data, list) else [data]):
            graph = node.get("@graph") if isinstance(node, dict) else None
            for n in (graph if isinstance(graph, list) else [node]):
                if not isinstance(n, dict):
                    continue
                types = n.get("@type") or ""
                if "JobPosting" not in (types if isinstance(types, str) else " ".join(map(str, types))):
                    continue
                org = n.get("hiringOrganization")
                head = [str(n.get("title") or ""), org.get("name", "") if isinstance(org, dict) else str(org or "")]
                body = _Text()
                body.feed(str(n.get("description") or ""))
                return tidy("\n".join([x for x in head if x] + [body.text()]))
    return ""


def from_html(html):
    parser = _Text()
    parser.feed(html)
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    return tidy("\n".join(filter(None, [tidy(title.group(1)) if title else "", parser.text()])))


def safe_url(url, resolve=None):
    """Normalize, then refuse anything that is not a public http(s) address. Raises JobPostError.
    `resolve` is the name lookup, injected by the tests so they never touch DNS.

    Note: the address is checked before the request, so a hostname that resolves to a public address and then
    to a private one (DNS rebinding) is not covered here. On Cloud Run the metadata server is the thing worth
    protecting and it is reached by IP, which this does block.
    """
    url = (url or "").strip()
    if url and "://" not in url:
        url = "https://" + url
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise JobPostError("That does not look like a web address. Paste a link starting with https://", "bad_url")
    try:
        infos = (resolve or socket.getaddrinfo)(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80),
                                                proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise JobPostError("We could not find that website. Check the address and try again.", "bad_url")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            raise JobPostError("That address is not reachable from the internet, so we cannot read it.",
                               "blocked_host")
    return urlunparse(parts._replace(fragment=""))


def fetch_job_text(url, get=None, resolve=None):
    """Return {'url', 'text', 'chars', 'source'} for a job posting page. Raises JobPostError with a message
    the UI can show. `get` and `resolve` are the HTTP getter and the name lookup, injected by the tests so
    they never touch the network."""
    if get is None:
        import requests
        get = requests.get

    target = safe_url(url, resolve)
    for _ in range(MAX_REDIRECTS + 1):
        try:
            res = get(target, timeout=TIMEOUT_S, allow_redirects=False, stream=True,
                      headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
        except Exception as e:
            raise JobPostError("We could not open that page. Paste the job description text instead.",
                               "fetch_failed") from e
        code = getattr(res, "status_code", 0)
        if code in (301, 302, 303, 307, 308):
            location = (getattr(res, "headers", {}) or {}).get("Location")
            if not location:
                raise JobPostError("That page redirected somewhere we could not follow.", "fetch_failed")
            target = safe_url(location if "://" in location else
                              urlunparse(urlparse(target)._replace(path=location, query="", fragment="")), resolve)
            continue
        break
    else:
        raise JobPostError("That page redirected too many times.", "fetch_failed")

    if code == 403 or code == 401:
        raise JobPostError("That site asks for a login before showing the posting. Open the link yourself and "
                           "paste the text instead.", "fetch_failed")
    if code != 200:
        raise JobPostError(f"That page answered {code}. Check the link, or paste the text instead.", "fetch_failed")

    ctype = (getattr(res, "headers", {}) or {}).get("Content-Type", "")
    if ctype and "html" not in ctype.lower() and "text" not in ctype.lower():
        raise JobPostError("That link is not a web page. Paste the job description text instead.", "not_html")

    body = getattr(res, "text", "") or ""
    if len(body) > MAX_BYTES:
        body = body[:MAX_BYTES]

    text = from_json_ld(body) or from_html(body)
    if len(text) < MIN_CHARS:
        raise JobPostError("We opened the page but could not find the posting, which usually means the site "
                           "needs a login or builds the page in the browser. Paste the text instead.",
                           "too_short")
    return {"url": target, "text": text[:MAX_CHARS], "chars": len(text), "source": url}
