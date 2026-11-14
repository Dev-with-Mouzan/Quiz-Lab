"""Fetch a teacher-supplied web page and extract its readable text.

Used as reference material for AI quiz generation, like document_text.py does for
uploaded files. The text is data only; it is never treated as instructions.

The server fetches a URL the user typed, so every hop is checked against SSRF:
only http/https on default ports, and the host must resolve to public addresses.
Residual risk: httpx resolves the host again when it connects, so a DNS answer
that changes between the check and the connect (DNS rebinding) is not caught.
"""
import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

from app.services.document_text import MAX_EXTRACTED_CHARS, _pdf_text
from app.services.question_bank import QuestionParseError

MAX_URL_LENGTH = 2000
MAX_PAGE_BYTES = 3 * 1024 * 1024
MAX_REDIRECTS = 5
FETCH_TIMEOUT_SECONDS = 15
USER_AGENT = "QuizLabBot/1.0 (+quiz drafting from a teacher-supplied page)"

_DEFAULT_PORTS = {"http": 80, "https": 443}
_SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "header",
              "aside", "iframe", "template", "button", "select"}
_VOID_TAGS = {"br", "hr", "img", "input", "meta", "link", "area", "base", "col",
              "embed", "source", "track", "wbr"}
_BLOCK_TAGS = {"p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
               "br", "tr", "td", "th", "section", "article", "main", "table",
               "blockquote", "pre", "dd", "dt", "figcaption", "hr"}


# ── HTML to text ──────────────────────────────────────────────────────────

class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in _VOID_TAGS:
            if tag in _BLOCK_TAGS and not self._skip_depth:
                self.parts.append("\n")
            return
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in _BLOCK_TAGS and not self._skip_depth:
            self.parts.append("\n")

    def handle_startendtag(self, tag, attrs):
        if tag in _BLOCK_TAGS and not self._skip_depth:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag == "title":
            self._in_title = False
        elif tag in _BLOCK_TAGS and not self._skip_depth:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title_parts.append(data)
        elif not self._skip_depth:
            self.parts.append(data)


def html_to_text(html: str) -> tuple[str, str]:
    """Return (title, text) of an HTML document, without scripts, menus and footers."""
    parser = _TextExtractor()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        pass  # keep whatever was parsed before the broken markup
    title = re.sub(r"\s+", " ", "".join(parser.title_parts)).strip()
    return title[:200], _normalise("".join(parser.parts))


def _normalise(text: str) -> str:
    lines = (re.sub(r"[ \t\r\f\v ]+", " ", line).strip() for line in text.split("\n"))
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# ── URL safety ────────────────────────────────────────────────────────────

def _is_public_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip.split("%")[0])
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return addr.is_global and not addr.is_multicast


def check_url(url: str) -> str:
    """Validate a URL and its resolved addresses. Return the cleaned URL."""
    url = (url or "").strip()
    if not url or len(url) > MAX_URL_LENGTH:
        raise QuestionParseError("Enter a valid web page link (up to 2000 characters).")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError as exc:
        raise QuestionParseError("This link is not a valid web address.") from exc
    scheme = parts.scheme.lower()
    if scheme not in _DEFAULT_PORTS:
        raise QuestionParseError("Only http:// and https:// links are supported.")
    if parts.username or parts.password:
        raise QuestionParseError("Links with a username or password are not supported.")
    host = parts.hostname
    if not host:
        raise QuestionParseError("This link is not a valid web address.")
    if port is not None and port != _DEFAULT_PORTS[scheme]:
        raise QuestionParseError("Links to non-standard ports are not supported.")

    try:
        infos = socket.getaddrinfo(host, _DEFAULT_PORTS[scheme], proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError) as exc:
        raise QuestionParseError("This website could not be found. Check the link.") from exc
    addresses = {info[4][0] for info in infos}
    if not addresses or not all(_is_public_ip(a) for a in addresses):
        raise QuestionParseError("This link points to a private or local address and cannot be used.")
    return url


# ── Fetching ──────────────────────────────────────────────────────────────

def _read_capped(resp: httpx.Response) -> bytes:
    declared = resp.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_PAGE_BYTES:
        raise QuestionParseError("This page is too large to read (max 3MB).")
    chunks, total = [], 0
    for chunk in resp.iter_bytes():
        total += len(chunk)
        if total > MAX_PAGE_BYTES:
            raise QuestionParseError("This page is too large to read (max 3MB).")
        chunks.append(chunk)
    return b"".join(chunks)


def _decode(body: bytes, resp: httpx.Response) -> str:
    charset = resp.charset_encoding
    if not charset:
        m = re.search(rb'<meta[^>]+charset=["\']?([A-Za-z0-9_-]+)', body[:4096], re.IGNORECASE)
        charset = m.group(1).decode("ascii") if m else "utf-8"
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def fetch_page_text(url: str) -> dict:
    """Fetch one page and return {"url", "title", "text"}.

    Raises QuestionParseError with a message that is safe to show the teacher.
    """
    current = check_url(url)
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,text/plain,application/pdf;q=0.9"}

    for _ in range(MAX_REDIRECTS + 1):
        try:
            with httpx.stream("GET", current, headers=headers, timeout=FETCH_TIMEOUT_SECONDS,
                              follow_redirects=False) as resp:
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("location")
                    if not location:
                        raise QuestionParseError("The page redirected without a destination.")
                    current = check_url(urljoin(current, location))
                    continue
                if resp.status_code >= 400:
                    raise QuestionParseError(
                        f"The page returned HTTP {resp.status_code}. It may not exist or may block automated access."
                    )
                content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
                body = _read_capped(resp)
                return _extract(current, content_type, body, resp)
        except QuestionParseError:
            raise
        except httpx.TimeoutException as exc:
            raise QuestionParseError("The page took too long to respond. Try again or use another link.") from exc
        except httpx.HTTPError as exc:
            raise QuestionParseError("The page could not be reached. Check the link and try again.") from exc

    raise QuestionParseError("The page redirected too many times.")


def _extract(url: str, content_type: str, body: bytes, resp: httpx.Response) -> dict:
    if content_type in ("text/html", "application/xhtml+xml", ""):
        title, text = html_to_text(_decode(body, resp))
    elif content_type == "text/plain":
        title, text = "", _normalise(_decode(body, resp))
    elif content_type == "application/pdf":
        title, text = "", _normalise(_pdf_text(body))
    else:
        raise QuestionParseError("This link is not a web page or PDF.")

    if len(text) < 50:
        raise QuestionParseError(
            "No readable text was found on this page. Pages that load their content "
            "with JavaScript are not supported; try copying the text into the notes instead."
        )
    return {"url": url, "title": title, "text": text[:MAX_EXTRACTED_CHARS]}
