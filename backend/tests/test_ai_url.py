"""AI question drafting from a web page link.

Both the AI provider and the page fetch are mocked; no real network is used.
The checks are: page text reaches the model, and private/local addresses are refused.

    TEST_DATABASE_URL=sqlite:///./test_final.db  python -m tests.test_ai_url
"""
import json
import socket
from contextlib import contextmanager

import httpx

from tests.helpers import (
    TestClient, app, check, finish, admin_login, create_teacher, teacher_login,
    register_student,
)
from app.dependencies.ratelimit import limiter
from app.services.web_text import html_to_text

REAL_POST = httpx.post
REAL_STREAM = httpx.stream
REAL_GETADDRINFO = socket.getaddrinfo
AI_CALLS = []
FETCHES = []

# host -> IP the fake DNS returns
DNS = {
    "example.edu": "93.184.216.34",
    "redirector.example.edu": "93.184.216.35",
    "internal.example.edu": "10.0.0.5",
    "v6local.example.edu": "::1",
}

ARTICLE_HTML = """<!doctype html><html><head><title>TCP Handshake | Networks 101</title>
<style>body { color: red }</style><script>alert('SCRIPT_TEXT')</script></head>
<body><nav>Home | About | NAV_TEXT</nav>
<header>SITE_HEADER_TEXT</header>
<main><h1>The TCP three-way handshake</h1>
<p>A client sends SYN, the server answers with SYN-ACK, and the client replies with ACK.</p>
<p>After the handshake both sides can exchange data reliably &amp; in order.</p></main>
<footer>FOOTER_TEXT copyright</footer></body></html>"""

# path -> (status, headers, body)
PAGES = {
    "https://example.edu/tcp": (200, {"content-type": "text/html; charset=utf-8"}, ARTICLE_HTML.encode()),
    "https://example.edu/plain": (200, {"content-type": "text/plain"},
                                  b"Binary search halves the search interval on every step of the loop."),
    "https://example.edu/image": (200, {"content-type": "image/png"}, b"\x89PNG...."),
    "https://example.edu/spa": (200, {"content-type": "text/html"},
                                b"<html><body><div id='root'></div><script>render()</script></body></html>"),
    "https://example.edu/missing": (404, {"content-type": "text/html"}, b"not found"),
    "https://example.edu/huge": (200, {"content-type": "text/html"}, b"<p>" + b"a" * (4 * 1024 * 1024)),
    "https://example.edu/urdu": (200, {"content-type": "text/html; charset=utf-8"},
                                 "<html><body><p>پاکستان کا دارالحکومت اسلام آباد ہے اور یہ ایک خوبصورت شہر ہے۔</p></body></html>".encode()),
    "https://redirector.example.edu/go": (302, {"location": "https://example.edu/tcp"}, b""),
    "https://redirector.example.edu/evil": (302, {"location": "http://internal.example.edu/admin"}, b""),
    "https://redirector.example.edu/meta": (302, {"location": "http://169.254.169.254/latest/meta-data/"}, b""),
}


def fake_getaddrinfo(host, port, *args, **kwargs):
    try:
        ip = DNS.get(host) or str(__import__("ipaddress").ip_address(host))
    except ValueError:
        raise socket.gaierror("unknown host")
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    return [(family, socket.SOCK_STREAM, 6, "", (ip, port))]


@contextmanager
def fake_stream(method, url, headers=None, timeout=None, follow_redirects=True):
    FETCHES.append(url)
    assert follow_redirects is False, "redirects must be followed manually"
    if url not in PAGES:
        raise httpx.ConnectError("unreachable")
    status, resp_headers, body = PAGES[url]
    yield httpx.Response(status, headers=resp_headers, content=body)


def fake_post(url, headers=None, json=None, timeout=None):
    AI_CALLS.append({"url": url, "json": json})
    questions = [
        {"text": "What does the server send after SYN?", "options": ["SYN-ACK", "FIN"], "correct_index": 0},
        {"text": "How many steps are in the handshake?", "options": ["Three", "Two"], "correct_index": 0},
    ]
    content = __import__("json").dumps({"questions": questions})
    return FakeResponse(200, {"choices": [{"message": {"content": content}}]})


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


# ── HTML to text, without the network ──
title, text = html_to_text(ARTICLE_HTML)
check("parser: title extracted", title == "TCP Handshake | Networks 101", title)
check("parser: article text kept", "server answers with SYN-ACK" in text and "reliably & in order" in text, text)
check("parser: script, style, nav, header and footer removed",
      not any(s in text for s in ("SCRIPT_TEXT", "color: red", "NAV_TEXT", "SITE_HEADER_TEXT", "FOOTER_TEXT")), text)
check("parser: paragraphs on separate lines", "\n" in text)
_, form_text = html_to_text("<html><body><form><p>Content inside an ASP.NET page form is kept.</p></form></body></html>")
check("parser: text inside <form> is kept", "Content inside" in form_text, form_text)


socket.getaddrinfo = fake_getaddrinfo
httpx.stream = fake_stream
try:
    with TestClient(app) as c:
        admin_h = admin_login(c)
        create_teacher(c, admin_h, "url.teacher@gmail.com")
        th = teacher_login(c, "url.teacher@gmail.com")
        student_h = register_student(c, "Url", "Student", "url.student@gmail.com", "36-URL-01", 2036)

        def gen(headers, url, **extra):
            body = {"url": url, "count": 2, "difficulty": "medium", "language": "English"}
            body.update(extra)
            return c.post("/api/ai/generate-from-url", headers=headers, json=body)

        def last_prompt():
            return AI_CALLS[-1]["json"]["messages"][1]["content"] if AI_CALLS else ""

        # Access and setup
        r = gen(student_h, "https://example.edu/tcp")
        check("student cannot generate from a link", r.status_code == 403, str(r.status_code))

        FETCHES.clear()
        r = gen(th, "https://example.edu/tcp")
        check("link without AI setup gives the profile message and fetches nothing",
              r.status_code == 400 and "profile" in r.json()["detail"].lower() and not FETCHES, r.text[:200])

        c.put("/api/ai/settings", headers=th, json={"provider": "openai", "model": "gpt-4o-mini",
                                                    "api_key": "sk-url-test-KEY1"})
        httpx.post = fake_post
        limiter.reset()

        # Happy path
        AI_CALLS.clear()
        r = gen(th, "https://example.edu/tcp")
        prompt = last_prompt()
        check("HTML page: questions drafted", r.status_code == 200 and len(r.json()["questions"]) == 2, r.text[:200])
        check("HTML page: page text reaches the model as reference material",
              "server answers with SYN-ACK" in prompt and "the web page provided below" in prompt
              and "Page title: TCP Handshake" in prompt, prompt[:300])
        check("HTML page: scripts and menus are not sent", "SCRIPT_TEXT" not in prompt and "NAV_TEXT" not in prompt)
        src = r.json().get("source", {})
        check("response describes the source page",
              src.get("title") == "TCP Handshake | Networks 101" and src.get("url") == "https://example.edu/tcp"
              and src.get("chars", 0) > 50, json.dumps(src))

        AI_CALLS.clear()
        r = gen(th, "https://example.edu/tcp", topic="TCP", notes="Focus on the ACK step")
        prompt = last_prompt()
        check("teacher topic and notes are used with the page text",
              r.status_code == 200 and "Topic: TCP" in prompt and "Focus on the ACK step" in prompt
              and "SYN-ACK" in prompt, prompt[:300])

        r = gen(th, "https://example.edu/plain")
        check("plain text page works", r.status_code == 200 and "halves the search" in last_prompt(), r.text[:200])

        r = gen(th, "https://example.edu/urdu", language="Urdu")
        check("Urdu page text is decoded correctly", r.status_code == 200 and "اسلام آباد" in last_prompt(), r.text[:200])
        limiter.reset()

        # Redirects
        FETCHES.clear()
        r = gen(th, "https://redirector.example.edu/go")
        check("public redirect is followed", r.status_code == 200 and FETCHES[-1] == "https://example.edu/tcp",
              f"{r.status_code} {FETCHES}")

        FETCHES.clear()
        r = gen(th, "https://redirector.example.edu/evil")
        check("redirect to a private address is refused",
              r.status_code == 400 and "private or local" in r.json()["detail"]
              and "http://internal.example.edu/admin" not in FETCHES, f"{r.text[:200]} {FETCHES}")

        r = gen(th, "https://redirector.example.edu/meta")
        check("redirect to cloud metadata address is refused",
              r.status_code == 400 and "private or local" in r.json()["detail"], r.text[:200])
        limiter.reset()

        # Blocked addresses: nothing is fetched for any of them
        blocked = [
            ("http://localhost/", None),  # fake DNS has no 'localhost' -> not found; real DNS -> loopback
            ("http://127.0.0.1/admin", "private or local"),
            ("http://169.254.169.254/latest/meta-data/", "private or local"),
            ("http://10.0.0.5/", "private or local"),
            ("http://[::1]/", "private or local"),
            ("http://internal.example.edu/", "private or local"),
            ("http://v6local.example.edu/", "private or local"),
            ("ftp://example.edu/file", "Only http"),
            ("file:///etc/passwd", "Only http"),
            ("http://user:pass@example.edu/", "username or password"),
            ("http://example.edu:8080/", "non-standard ports"),
        ]
        for url, expect in blocked:
            limiter.reset()
            FETCHES.clear()
            r = gen(th, url)
            ok = r.status_code in (400, 422) and not FETCHES
            if expect and r.status_code == 400:
                ok = ok and expect in r.json()["detail"]
            check(f"refused without fetching: {url}", ok, f"{r.status_code} {r.text[:150]} {FETCHES}")
        limiter.reset()

        # Content problems
        r = gen(th, "https://example.edu/image")
        check("non-page content type refused", r.status_code == 400 and "not a web page" in r.json()["detail"], r.text[:200])

        r = gen(th, "https://example.edu/spa")
        check("JavaScript-only page gives the no-readable-text message",
              r.status_code == 400 and "No readable text" in r.json()["detail"], r.text[:200])

        r = gen(th, "https://example.edu/missing")
        check("HTTP 404 page gives a friendly error", r.status_code == 400 and "HTTP 404" in r.json()["detail"], r.text[:200])

        r = gen(th, "https://example.edu/huge")
        check("page over 3MB refused", r.status_code == 400 and "too large" in r.json()["detail"], r.text[:200])
        limiter.reset()

        r = gen(th, "https://nowhere.invalid/")
        check("unknown host gives a friendly error", r.status_code == 400 and "could not be found" in r.json()["detail"], r.text[:200])

        r = gen(th, "not a url at all")
        check("garbage link refused", r.status_code == 400, r.text[:200])
finally:
    httpx.post = REAL_POST
    httpx.stream = REAL_STREAM
    socket.getaddrinfo = REAL_GETADDRINFO

finish()
