"""Accounts: admin login, teacher creation and login, student registration with OTP.

    TEST_DATABASE_URL=sqlite:///./test_final.db  python -m tests.test_accounts
"""
from tests.helpers import TestClient, app, settings, check, finish, auth, register_student

with TestClient(app) as c:
    # ── Auth: admin login (credentials come from settings, never from source) ──
    r = c.post("/api/auth/login", json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD})
    check("admin login", r.status_code == 200, str(r.status_code))
    admin_h = auth(r.json()["access_token"])

    # ── Admin creates a teacher ──
    r = c.post("/api/users/", headers=admin_h, json={
        "first_name": "Tina", "last_name": "Teacher", "email": "accounts.teacher@gmail.com",
        "password": "Teacher@123", "role_name": "teacher", "department": "CS",
    })
    check("admin creates teacher", r.status_code == 201, f"{r.status_code} {r.text[:200]}")

    # ── Teacher login ──
    r = c.post("/api/auth/login", json={"email": "accounts.teacher@gmail.com", "password": "Teacher@123"})
    check("teacher login", r.status_code == 200, str(r.status_code))

    # ── Student registration + OTP verification ──
    register_student(c, "Acc", "Student", "accounts.student@gmail.com", "32-ACC-01", enrollment_year=2032)

finish()
