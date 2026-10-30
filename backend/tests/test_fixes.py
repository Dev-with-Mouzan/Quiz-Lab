"""Regression checks for the security and correctness fixes.

Needs a THROWAWAY database (the name must contain 'test'):

    TEST_DATABASE_URL=sqlite:///./test_fixes.db  python tests/test_fixes.py   (from backend/)
"""
import os
import sys

_TEST_DB = os.environ.get("TEST_DATABASE_URL", "")
if not _TEST_DB or "test" not in _TEST_DB.lower():
    sys.exit("Set TEST_DATABASE_URL to a throwaway database whose name contains 'test'.")
os.environ["DATABASE_URL"] = _TEST_DB
os.environ["EMAIL_PROVIDER"] = "console"  # never send real mail from a test run
os.environ["COOKIE_SECURE"] = "false"     # TestClient talks plain http; Secure cookies would not be sent

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.database.database import SessionLocal
from app.dependencies.auth import pwd_context
from app.models import User, OTPVerification

PASS = []
FAIL = []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(f"{'PASS' if cond else 'FAIL'}: {name} {extra}")


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def register(c, first, email, roll, semester=1):
    return c.post("/api/auth/register", json={
        "first_name": first, "last_name": "Test", "email": email,
        "password": "Student@123", "confirm_password": "Student@123",
        "roll_number": roll, "semester": semester, "enrollment_year": 2026,
        "department": "CS", "session_type": "morning",
    })


def verify_student(c, email):
    """Register-then-verify helper: plants a known OTP, as the smoke test does."""
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).one()
        rec = (db.query(OTPVerification)
               .filter(OTPVerification.user_id == u.id, OTPVerification.is_used == False,  # noqa: E712
                       OTPVerification.purpose == "registration")
               .order_by(OTPVerification.created_at.desc()).first())
        rec.otp_hash = pwd_context.hash("123456")
        db.commit()
    finally:
        db.close()
    return c.post("/api/auth/verify-otp", json={"email": email, "otp_code": "123456"})


with TestClient(app) as c:
    admin = c.post("/api/auth/login", json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD}).json()
    admin_h = auth(admin["access_token"])

    # 1. Admin-created emails are stored lowercase, and login works with any casing
    r = c.post("/api/users/", headers=admin_h, json={
        "first_name": "Tina", "last_name": "Teacher", "email": "Tina.Mixed@Gmail.com",
        "password": "Teacher@123", "role_name": "teacher",
    })
    check("admin creates teacher with mixed-case email", r.status_code == 201, str(r.status_code))
    teacher_id = r.json().get("id")
    check("stored email is lowercase", r.json().get("email") == "tina.mixed@gmail.com", r.json().get("email", ""))
    r = c.post("/api/auth/login", json={"email": "TINA.MIXED@gmail.com", "password": "Teacher@123"})
    check("login with different casing succeeds", r.status_code == 200, str(r.status_code))
    teacher_h = auth(r.json()["access_token"])

    # 2. Unverified accounts: login works, profile works, protected endpoints refuse
    register(c, "Una", "una.pending@gmail.com", "26-CS-50")
    r = c.post("/api/auth/login", json={"email": "una.pending@gmail.com", "password": "Student@123"})
    check("unverified login returns is_verified=false", r.status_code == 200 and r.json()["is_verified"] is False)
    una_h = auth(r.json()["access_token"])
    r = c.get("/api/auth/me", headers=una_h)
    check("unverified user can read /me", r.status_code == 200 and r.json()["is_verified"] is False, str(r.status_code))
    r = c.get("/api/quizzes", headers=una_h)
    check("unverified user blocked from /api/quizzes", r.status_code == 403, str(r.status_code))
    # Session cookie: the login response set it, so no Authorization header is needed
    r = c.get("/api/auth/me")
    check("session cookie authenticates /me without a header",
          r.status_code == 200 and r.json()["email"] == "una.pending@gmail.com", str(r.status_code))
    r = c.post("/api/auth/login", json={"email": "una.pending@gmail.com", "password": "Student@123"})
    check("login response sets an HttpOnly access_token cookie",
          "access_token" in r.headers.get("set-cookie", "") and "httponly" in r.headers.get("set-cookie", "").lower())

    # Already-verified accounts must not yield a token without an OTP
    r = c.post("/api/auth/verify-otp", json={"email": "tina.mixed@gmail.com", "otp_code": "000000"})
    check("verify-otp on a verified account issues no token", r.status_code == 400 and "access_token" not in r.text,
          str(r.status_code))

    # 3. Enumeration: unknown accounts get the same answer as known ones
    r1 = c.post("/api/auth/forgot-password", json={"email": "nobody.here@gmail.com"})
    r2 = c.post("/api/auth/forgot-password", json={"email": "una.pending@gmail.com"})
    check("forgot-password is identical for unknown and known email",
          r1.status_code == 200 and r2.status_code == 200 and r1.json() == r2.json(),
          f"{r1.status_code} {r2.status_code}")
    r = c.post("/api/auth/verify-otp", json={"email": "nobody.here@gmail.com", "otp_code": "000000"})
    check("verify-otp for unknown email is 400 (not 404)", r.status_code == 400, str(r.status_code))

    # 4. Course ownership must be a teacher account
    student_verify = verify_student(c, "una.pending@gmail.com")
    check("verify-otp activates account", student_verify.status_code == 200, str(student_verify.status_code))
    una_id = c.get("/api/auth/me", headers=una_h).json()["id"]
    r = c.post("/api/courses/", headers=admin_h, json={
        "course_code": "FIX101", "title": "Fix Test", "description": "x", "semester": 1,
        "session": "26-30", "session_type": "morning", "teacher_id": una_id,
    })
    check("course cannot be owned by a student", r.status_code == 400, str(r.status_code))
    r = c.post("/api/courses/", headers=admin_h, json={
        "course_code": "FIX102", "title": "Fix Test", "description": "x", "semester": 1,
        "session": "26-30", "session_type": "morning", "teacher_id": teacher_id,
    })
    check("course owned by a teacher is created", r.status_code == 201, str(r.status_code))
    course_id = r.json().get("id")

    # 5. Malformed quiz payload is a 400, not a server error
    r = c.post("/api/quizzes", headers=teacher_h,
               data={"course_id": course_id, "title": "Bad", "questions": "not-json"})
    check("malformed questions JSON -> 400", r.status_code == 400, str(r.status_code))
    r = c.post("/api/quizzes", headers=teacher_h,
               data={"course_id": course_id, "title": "Bad", "questions": '[{"text":"Q","options":["a","b"],"correct":"zz"}]'})
    check("non-numeric correct answer -> 400", r.status_code == 400, str(r.status_code))
    r = c.post("/api/quizzes", headers=teacher_h,
               data={"course_id": course_id, "title": "Bad", "questions": '["just a string"]'})
    check("non-object question -> 400", r.status_code == 400, str(r.status_code))

    # 6. Rate limits are enforced on decorated routes (parse-file allows 10/minute)
    csv_body = b"Question,A,B,Answer\r\nWhat?,1,2,B\r\n"
    statuses = []
    for _ in range(11):
        r = c.post("/api/quizzes/parse-file", headers=teacher_h,
                   files={"file": ("bank.csv", csv_body, "text/csv")})
        statuses.append(r.status_code)
    check("11th parse-file call in a minute is rate-limited (429)",
          statuses[:10].count(429) == 0 and statuses[10] == 429, str(statuses))

    # 7. Partial promotion must not archive the whole class's courses
    for name, email, roll in [("Ali", "ali.class@gmail.com", "26-CS-60"), ("Bilal", "bilal.class@gmail.com", "26-CS-61")]:
        register(c, name, email, roll)
        verify_student(c, email)
    db = SessionLocal()
    try:
        ids = {u.email: u.id for u in db.query(User).filter(User.email.in_(["ali.class@gmail.com", "bilal.class@gmail.com"])).all()}
    finally:
        db.close()
    # Three students are in semester 1 (Ali, Bilal, and Una from step 2).
    # Promote Ali: Bilal and Una still need the course, so it must stay active.
    r = c.post("/api/users/promotion/promote", headers=admin_h,
               json={"student_ids": [ids["ali.class@gmail.com"]], "to_semester": 2})
    check("promote one student", r.status_code == 200, str(r.status_code))
    course = next(x for x in c.get("/api/courses/", headers=admin_h).json() if x["id"] == course_id)
    check("course stays active while classmates remain in the semester", course["is_active"] is True)
    r = c.post("/api/users/promotion/promote", headers=admin_h,
               json={"student_ids": [ids["bilal.class@gmail.com"], una_id], "to_semester": 2})
    course = next(x for x in c.get("/api/courses/", headers=admin_h).json() if x["id"] == course_id)
    check("course archived once the whole semester has moved on", r.status_code == 200 and course["is_active"] is False)

    # 8. Hard delete of a teacher whose quiz has student attempts (course reassigned away)
    register(c, "Sami", "sami.quiz@gmail.com", "26-CS-70", semester=1)
    verify_student(c, "sami.quiz@gmail.com")
    sami_h = auth(c.post("/api/auth/login", json={"email": "sami.quiz@gmail.com", "password": "Student@123"}).json()["access_token"])
    course_r = c.post("/api/courses/", headers=admin_h, json={
        "course_code": "FIX200", "title": "Quiz Course", "description": "x", "semester": 1,
        "session": "26-30", "session_type": "morning", "teacher_id": teacher_id,
    })
    quiz_course_id = course_r.json()["id"]
    r = c.post("/api/quizzes", headers=teacher_h, data={
        "course_id": quiz_course_id, "title": "Delete me later",
        "questions": '[{"text":"Q1","options":["a","b"],"correct":0},{"text":"Q2","options":["a","b"],"correct":1}]',
    })
    check("teacher creates quiz", r.status_code == 201, str(r.status_code))
    quiz_id = r.json()["id"]
    detail = c.get(f"/api/quizzes/{quiz_id}", headers=sami_h).json()
    answers = [{"question_id": q["id"], "selected_index": 0} for q in detail["questions"]]
    r = c.post(f"/api/quizzes/{quiz_id}/submit", headers=sami_h, json={"answers": answers})
    check("student submits attempt", r.status_code == 200, str(r.status_code))
    # reassign the course to a second teacher, then delete the first teacher
    tina2 = c.post("/api/users/", headers=admin_h, json={
        "first_name": "Second", "last_name": "Teacher", "email": "second.teacher@gmail.com",
        "password": "Teacher@123", "role_name": "teacher",
    }).json()["id"]
    c.put(f"/api/courses/{quiz_course_id}", headers=admin_h, json={"teacher_id": tina2})
    r = c.delete(f"/api/users/{teacher_id}/hard", headers=admin_h)
    check("hard delete of a teacher with attempted quizzes succeeds", r.status_code == 200, f"{r.status_code} {r.text[:200]}")

    # 9. Admin cannot delete their own account
    my_id = c.get("/api/auth/me", headers=admin_h).json()["id"]
    r = c.delete(f"/api/users/{my_id}/hard", headers=admin_h)
    check("admin cannot hard-delete own account", r.status_code == 400, str(r.status_code))

    # 10. Logout clears the session cookie
    c.post("/api/auth/login", json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD})
    check("cookie session is active before logout", c.get("/api/auth/me").status_code == 200)
    r = c.post("/api/auth/logout")
    check("logout succeeds", r.status_code == 200, str(r.status_code))
    check("session is gone after logout", c.get("/api/auth/me").status_code == 401)

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILED:", FAIL)
    sys.exit(1)
