"""Security checks: signup does not reveal existing accounts, API docs are off,
and the HSTS and CSP headers are sent.

    TEST_DATABASE_URL=sqlite:///./test_final.db  python -m tests.test_security
"""
from tests.helpers import TestClient, app, check, finish, admin_login, create_teacher, STUDENT_PASSWORD


def signup_body(email, roll):
    return {
        "first_name": "Sec", "last_name": "Test", "email": email,
        "password": STUDENT_PASSWORD, "confirm_password": STUDENT_PASSWORD,
        "roll_number": roll, "semester": 1, "enrollment_year": 2035,
        "department": "CS", "session_type": "morning",
    }


with TestClient(app) as c:
    admin_h = admin_login(c)
    create_teacher(c, admin_h, "sec.existing@gmail.com")  # a verified account already exists

    # 1. A verified email cannot sign up again; a new email can
    new = c.post("/api/auth/register", json=signup_body("sec.brandnew@gmail.com", "35-SEC-01"))
    existing = c.post("/api/auth/register", json=signup_body("sec.existing@gmail.com", "35-SEC-02"))
    check("signup: new email is accepted", new.status_code == 201, f"{new.status_code} {new.text[:150]}")
    check("signup: existing verified email is refused with 400",
          existing.status_code == 400 and "already exists" in existing.json().get("detail", ""),
          f"{existing.status_code} {existing.text[:150]}")
    check("signup: refusal tells the person to sign in or reset",
          "sign in" in existing.json().get("detail", "").lower(), existing.text[:200])

    # 2. API docs are off by default
    for path in ("/docs", "/redoc", "/openapi.json"):
        r = c.get(path)
        check(f"api docs off: {path} is 404", r.status_code == 404, str(r.status_code))

    # 3. Security headers on API responses
    r = c.get("/api/health")
    h = {k.lower(): v for k, v in r.headers.items()}
    check("HSTS header sent",
          h.get("strict-transport-security", "").startswith("max-age=31536000"), h.get("strict-transport-security"))
    check("CSP header sent (no content loaded, no framing)",
          h.get("content-security-policy") == "default-src 'none'; frame-ancestors 'none'",
          h.get("content-security-policy"))
    check("existing headers still present",
          h.get("x-content-type-options") == "nosniff" and h.get("x-frame-options") == "DENY")

finish()
