"""AI question drafting from uploaded slides and notes (PDF, DOCX, PPTX).

The provider is mocked. The check is that the extracted text is what the model sees.

    TEST_DATABASE_URL=sqlite:///./test_final.db  python -m tests.test_ai_files
"""
import io
import json
import zipfile

import httpx

from tests.helpers import (
    TestClient, app, check, finish, admin_login, create_teacher, teacher_login,
    register_student, make_docx,
)
from app.dependencies.ratelimit import limiter

REAL_POST = httpx.post
CALLS = []


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def fake_post(url, headers=None, json=None, timeout=None):
    CALLS.append({"url": url, "headers": headers or {}, "json": json})
    questions = [
        {"text": "Which layer routes packets?", "options": ["Network", "Transport"], "correct_index": 0},
        {"text": "What does HTTP stand for?", "options": ["Hypertext Transfer Protocol", "High Transfer"], "correct_index": 0},
    ]
    return FakeResponse(200, {"choices": [{"message": {"content": json_dumps({"questions": questions})}}]})


def json_dumps(obj):
    import json as _json
    return _json.dumps(obj)


def make_pptx(slides):
    """Minimal PPTX: one slide XML per entry, with the given text lines."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        for i, lines in enumerate(slides, start=1):
            paras = "".join(
                f'<a:p><a:r><a:t>{line}</a:t></a:r></a:p>' for line in lines
            )
            xml = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                f'<p:cSld><p:spTree>{paras}</p:spTree></p:cSld></p:sld>'
            )
            zf.writestr(f"ppt/slides/slide{i}.xml", xml)
    buf.seek(0)
    return buf


DOCX_NOTES = [
    "Networking basics: the network layer routes packets between hosts across routers.",
    "The transport layer provides reliable delivery with TCP and best-effort delivery with UDP.",
    "HTTP is an application layer protocol used by web browsers and servers.",
]

PPTX_SLIDES = [
    ["Databases", "A relational database stores data in tables linked by keys."],
    ["Normalization", "Third normal form removes transitive dependencies between non-key columns."],
]

with TestClient(app) as c:
    admin_h = admin_login(c)
    create_teacher(c, admin_h, "files.teacher@gmail.com")
    th = teacher_login(c, "files.teacher@gmail.com")
    student_h = register_student(c, "Files", "Student", "files.student@gmail.com", "36-FIL-01", 2036)

    def upload(headers, filename, content, **form):
        data = {"count": "2", "difficulty": "medium", "language": "English", "topic": "", "notes": ""}
        data.update(form)
        return c.post("/api/ai/generate-from-file", headers=headers, data=data,
                      files={"file": (filename, content, "application/octet-stream")})

    # Access and setup
    r = upload(student_h, "notes.docx", make_docx(DOCX_NOTES))
    check("student cannot generate from files", r.status_code == 403, str(r.status_code))

    r = upload(th, "notes.docx", make_docx(DOCX_NOTES))
    check("file upload without AI setup gives the profile message",
          r.status_code == 400 and "profile" in r.json()["detail"].lower(), r.text[:200])

    c.put("/api/ai/settings", headers=th, json={"provider": "openai", "model": "gpt-4o-mini",
                                                "api_key": "sk-files-test-KEY1"})
    httpx.post = fake_post

    # DOCX slides/notes
    CALLS.clear()
    r = upload(th, "notes.docx", make_docx(DOCX_NOTES), topic="Networking")
    check("DOCX: questions drafted", r.status_code == 200 and len(r.json()["questions"]) == 2, r.text[:200])
    prompt = CALLS[0]["json"]["messages"][1]["content"] if CALLS else ""
    check("DOCX: extracted text reaches the model",
          "routes packets between hosts" in prompt and "Topic: Networking" in prompt, prompt[:200])

    # PPTX slides, topic left empty
    CALLS.clear()
    r = upload(th, "lecture.pptx", make_pptx(PPTX_SLIDES))
    prompt = CALLS[0]["json"]["messages"][1]["content"] if CALLS else ""
    check("PPTX: questions drafted and slide text reaches the model",
          r.status_code == 200 and "Slide 1:" in prompt and "transitive dependencies" in prompt
          and "the material provided below" in prompt, r.text[:200])

    # Teacher notes and file together
    CALLS.clear()
    r = upload(th, "lecture.pptx", make_pptx(PPTX_SLIDES), notes="Focus on normal forms")
    prompt = CALLS[0]["json"]["messages"][1]["content"] if CALLS else ""
    check("teacher notes are included with the file text",
          r.status_code == 200 and "Focus on normal forms" in prompt and "Slide 2:" in prompt)

    # The upload endpoint allows 5 calls a minute, so reset the counter between groups
    limiter.reset()

    # Unsupported type
    r = upload(th, "notes.txt", b"plain text content that is long enough to matter here, yes indeed")
    check("unsupported file type refused",
          r.status_code == 400 and "PDF, DOCX or PPTX" in r.json()["detail"], r.text[:200])

    # Nothing readable
    r = upload(th, "empty.docx", make_docx(["hi"]))
    check("file with no readable text refused",
          r.status_code == 400 and "No readable text" in r.json()["detail"], r.text[:200])

    # Too large
    r = upload(th, "big.docx", b"0" * (11 * 1024 * 1024))
    check("file over 10MB refused", r.status_code == 400 and "too large" in r.json()["detail"], r.text[:200])

    # Zip bomb guard: a small file that expands past the limit
    bomb = io.BytesIO()
    with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("ppt/slides/slide1.xml", b"0" * (51 * 1024 * 1024))
    bomb.seek(0)
    r = upload(th, "bomb.pptx", bomb.getvalue())
    check("zip that expands too much is refused",
          r.status_code == 400 and "too much data" in r.json()["detail"], r.text[:200])

    # PDF: works when pypdf is installed, otherwise says what to do
    try:
        import pypdf  # noqa: F401
        pdf_available = True
    except ImportError:
        pdf_available = False
    r = upload(th, "slides.pdf", b"%PDF-1.4\n%not really a pdf\n")
    if pdf_available:
        check("PDF: broken file gives a friendly error", r.status_code == 400
              and "could not be read" in r.json()["detail"], r.text[:200])
    else:
        check("PDF: tells the admin to install PDF support",
              r.status_code == 400 and "pip install -r requirements.txt" in r.json()["detail"], r.text[:200])

    httpx.post = REAL_POST

finish()
