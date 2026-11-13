"""Shared setup for the final-project test files (test_*.py).

Each test_*.py file imports this module, so the environment guard, the
check() runner and the data helpers live here once. Every file builds its own
teacher, course and students, using unique emails, roll numbers and course
codes, and its own enrollment year (a student's session is derived from it, so
each file gets a separate course roster). That lets the files run in any order
against the same throwaway database.

Import this module before anything from `app`, because the app reads
DATABASE_URL at import time.
"""
import io
import os
import sys
import zipfile

_TEST_DB = os.environ.get("TEST_DATABASE_URL", "")
if not _TEST_DB or "test" not in _TEST_DB.lower():
    sys.exit("Set TEST_DATABASE_URL to a throwaway database whose name contains 'test'. "
             "Refusing to run against the main DATABASE_URL.")
os.environ["DATABASE_URL"] = _TEST_DB
os.environ["EMAIL_PROVIDER"] = "console"  # never send real mail from a test run

from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.database.database import SessionLocal  # noqa: E402
from app.dependencies.auth import pwd_context  # noqa: E402
from app.models import User, OTPVerification  # noqa: E402

__all__ = [
    "TestClient", "app", "settings", "SessionLocal",
    "check", "finish", "auth", "session_label", "admin_login", "create_teacher",
    "teacher_login", "create_course", "user_id", "register_student", "class_setup",
    "CSV_BANK", "make_docx", "DOCX_MIME",
]

STUDENT_PASSWORD = "Student@123"
TEACHER_PASSWORD = "Teacher@123"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

PASS = []
FAIL = []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(f"{'PASS' if cond else 'FAIL'}: {name} {extra}")


def finish():
    """Print the summary and exit non-zero if any check failed."""
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("FAILED:", FAIL)
        sys.exit(1)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def session_label(enrollment_year):
    """Matches the backend's session label, e.g. 2026 -> '26-30'."""
    return f"{enrollment_year % 100:02d}-{(enrollment_year + 4) % 100:02d}"


def admin_login(c):
    r = c.post("/api/auth/login", json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD})
    check("admin login", r.status_code == 200, str(r.status_code))
    return auth(r.json()["access_token"])


def create_teacher(c, admin_h, email, first="Tina", last="Teacher"):
    r = c.post("/api/users/", headers=admin_h, json={
        "first_name": first, "last_name": last, "email": email,
        "password": TEACHER_PASSWORD, "role_name": "teacher", "department": "CS",
    })
    check("admin creates teacher", r.status_code == 201, f"{r.status_code} {r.text[:200]}")
    return r.json()["id"]


def teacher_login(c, email):
    r = c.post("/api/auth/login", json={"email": email, "password": TEACHER_PASSWORD})
    check("teacher login", r.status_code == 200, str(r.status_code))
    return auth(r.json()["access_token"])


def create_course(c, admin_h, teacher_id, course_code, session, title="Intro to CS"):
    r = c.post("/api/courses/", headers=admin_h, json={
        "course_code": course_code, "title": title, "description": "Basics",
        "semester": 1, "session": session, "session_type": "morning", "teacher_id": teacher_id,
    })
    check("admin creates course", r.status_code == 201, f"{r.status_code} {r.text[:200]}")
    return r.json()["id"]


def user_id(email):
    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == email).one().id
    finally:
        db.close()


def plant_known_otp(email):
    """OTPs are stored hashed, so the code can't be read back. Overwrite the
    stored hash with a known code (email delivery is the console in tests)."""
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).one()
        rec = (db.query(OTPVerification)
               .filter(OTPVerification.user_id == u.id, OTPVerification.is_used == False)  # noqa: E712
               .order_by(OTPVerification.created_at.desc()).first())
        rec.otp_hash = pwd_context.hash("123456")
        db.commit()
    finally:
        db.close()


def register_student(c, first, last, email, roll, enrollment_year, semester=1):
    """Register, plant a known OTP, verify it. Returns the student's auth headers."""
    r = c.post("/api/auth/register", json={
        "first_name": first, "last_name": last, "email": email,
        "password": STUDENT_PASSWORD, "confirm_password": STUDENT_PASSWORD,
        "roll_number": roll, "semester": semester, "enrollment_year": enrollment_year,
        "department": "CS", "session_type": "morning",
    })
    check(f"register {first}", r.status_code == 201, f"{r.status_code} {r.text[:200]}")
    plant_known_otp(email)
    r = c.post("/api/auth/verify-otp", json={"email": email, "otp_code": "123456"})
    check(f"verify OTP {first}", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
    return auth(r.json()["access_token"])


def class_setup(c, tag, enrollment_year, course_code):
    """Build one self-contained class: admin session, a teacher, a course, and
    two students (Sami and Sara) who are enrolled in that course.

    `tag` must be unique per test file. It drives the emails and roll numbers.
    Returns a dict with: admin_h, teacher_id, th, course_id, session,
    s1, s2 (student auth headers), sami_id, sara_id.
    """
    admin_h = admin_login(c)
    teacher_email = f"{tag}.teacher@gmail.com"
    teacher_id = create_teacher(c, admin_h, teacher_email)
    session = session_label(enrollment_year)
    course_id = create_course(c, admin_h, teacher_id, course_code, session)
    th = teacher_login(c, teacher_email)

    yy = enrollment_year % 100
    sami_email = f"{tag}.sami@gmail.com"
    sara_email = f"{tag}.sara@gmail.com"
    s1 = register_student(c, "Sami", "Student", sami_email, f"{yy:02d}-{tag.upper()}-01", enrollment_year)
    s2 = register_student(c, "Sara", "Student", sara_email, f"{yy:02d}-{tag.upper()}-02", enrollment_year)

    return {
        "admin_h": admin_h, "teacher_id": teacher_id, "th": th, "course_id": course_id,
        "session": session, "s1": s1, "s2": s2,
        "sami_id": user_id(sami_email), "sara_id": user_id(sara_email),
    }


# ── Question-bank fixtures ──

CSV_BANK = (
    "Question,Option A,Option B,Option C,Option D,Answer\r\n"
    "What is 2+2?,3,4,5,6,B\r\n"
    "Capital of France?,Berlin,Paris,Rome,Madrid,B\r\n"
    "HTTP default port?,80,443,8080,3000,A\r\n"
    "SQL means?,Structured Query Language,Sequential Query Logic,Simple Query Language,Some Query Language,A\r\n"
    "1 byte = ?,6 bits,8 bits,16 bits,4 bits,B\r\n"
    "2^10 = ?,512,1024,2048,4096,B\r\n"
    "OSI layers?,5,7,4,6,B\r\n"
    "Git clone cmd?,git push,git pull,git clone,git init,C\r\n"
    "Avg quicksort?,O(n),O(n log n),O(n^2),O(log n),B\r\n"
    "RAM is?,volatile,non-volatile,permanent,write-once,A\r\n"
).encode()


def make_docx(paragraphs):
    """Build a minimal .docx (in memory) with one paragraph per string."""
    doc_xml = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
               '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>']
    for p in paragraphs:
        doc_xml.append(f'<w:p><w:r><w:t xml:space="preserve">{p}</w:t></w:r></w:p>')
    doc_xml.append('</w:body></w:document>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')
        zf.writestr("word/document.xml", "".join(doc_xml))
    buf.seek(0)
    return buf
