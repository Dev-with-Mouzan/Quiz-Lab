"""OTP brute-force protection.

Each round allows 3 wrong codes on the same OTP. After the 3rd wrong code, OTP entry
is locked for 5 minutes (no guesses and no new OTP). After the wait, the same OTP
gets the next 3 guesses. Requesting a new OTP does not reset the count.
Covers both signup (registration) and password reset.

    TEST_DATABASE_URL=sqlite:///./test_final.db  python -m tests.test_otp_lockout
"""
from datetime import timedelta

from tests.helpers import TestClient, app, check, finish, plant_known_otp, SessionLocal, STUDENT_PASSWORD
from app.models import User, OTPVerification, utcnow

WRONG_CODES = ["000001", "000002", "000003"]
CORRECT = "123456"  # planted by plant_known_otp


def expire_lock(email, purpose):
    """Simulate time passing: move the lock into the past."""
    db = SessionLocal()
    try:
        uid = db.query(User).filter(User.email == email).one().id
        db.query(OTPVerification).filter(
            OTPVerification.user_id == uid,
            OTPVerification.purpose == purpose,
            OTPVerification.locked_until.isnot(None),
        ).update({"locked_until": utcnow() - timedelta(seconds=1)})
        db.commit()
    finally:
        db.close()


def otp_count(email, purpose):
    db = SessionLocal()
    try:
        uid = db.query(User).filter(User.email == email).one().id
        return db.query(OTPVerification).filter(
            OTPVerification.user_id == uid, OTPVerification.purpose == purpose).count()
    finally:
        db.close()


with TestClient(app) as c:
    # ── Signup OTP lock ──
    email = "otp.lock.signup@gmail.com"
    r = c.post("/api/auth/register", json={
        "first_name": "Lock", "last_name": "Test", "email": email,
        "password": STUDENT_PASSWORD, "confirm_password": STUDENT_PASSWORD,
        "roll_number": "33-LOCK-01", "semester": 1, "enrollment_year": 2033,
        "department": "CS", "session_type": "morning",
    })
    check("signup: register", r.status_code == 201, str(r.status_code))
    plant_known_otp(email)

    r1 = c.post("/api/auth/verify-otp", json={"email": email, "otp_code": WRONG_CODES[0]})
    check("signup: wrong guess 1 is 400 with 2 attempts left",
          r1.status_code == 400 and r1.json().get("attempts_left") == 2, r1.text[:200])
    r2 = c.post("/api/auth/verify-otp", json={"email": email, "otp_code": WRONG_CODES[1]})
    check("signup: wrong guess 2 is 400 with 1 attempt left",
          r2.status_code == 400 and r2.json().get("attempts_left") == 1, r2.text[:200])
    r3 = c.post("/api/auth/verify-otp", json={"email": email, "otp_code": WRONG_CODES[2]})
    check("signup: 3rd wrong guess locks (429) with 0 left and a wait time",
          r3.status_code == 429 and r3.json().get("attempts_left") == 0
          and 0 < r3.json().get("locked_seconds", 0) <= 300, r3.text[:200])
    check("signup: lock message says 5 minutes",
          "5 minutes" in r3.json().get("detail", ""), r3.text[:200])

    r = c.post("/api/auth/verify-otp", json={"email": email, "otp_code": CORRECT})
    check("signup: correct code rejected during lock", r.status_code == 429, str(r.status_code))
    r = c.post("/api/auth/resend-otp", json={"email": email})
    check("signup: new OTP refused during lock", r.status_code == 429, str(r.status_code))

    # The same OTP stays valid after the wait: no re-request needed
    expire_lock(email, "registration")
    r = c.post("/api/auth/verify-otp", json={"email": email, "otp_code": CORRECT})
    check("signup: after lock, the SAME OTP works", r.status_code == 200, f"{r.status_code} {r.text[:150]}")

    # ── Password reset OTP lock ──
    reset_email = "otp.lock.reset@gmail.com"
    r = c.post("/api/auth/register", json={
        "first_name": "Reset", "last_name": "Test", "email": reset_email,
        "password": STUDENT_PASSWORD, "confirm_password": STUDENT_PASSWORD,
        "roll_number": "33-LOCK-02", "semester": 1, "enrollment_year": 2033,
        "department": "CS", "session_type": "morning",
    })
    check("reset: register", r.status_code == 201, str(r.status_code))
    plant_known_otp(reset_email)
    c.post("/api/auth/verify-otp", json={"email": reset_email, "otp_code": CORRECT})  # verify signup first
    new_pw = {"email": reset_email, "new_password": "NewPass@123"}

    c.post("/api/auth/forgot-password", json={"email": reset_email})
    plant_known_otp(reset_email)
    before = otp_count(reset_email, "password_reset")
    rr = [c.post("/api/auth/reset-password", json={**new_pw, "otp_code": code}) for code in WRONG_CODES]
    check("reset: wrong guesses 1-2 are 400", [x.status_code for x in rr[:2]] == [400, 400],
          str([x.status_code for x in rr]))
    check("reset: 3rd wrong guess locks (429)", rr[2].status_code == 429, str(rr[2].status_code))

    r = c.post("/api/auth/reset-password", json={**new_pw, "otp_code": CORRECT})
    check("reset: correct code rejected during lock", r.status_code == 429, str(r.status_code))
    r = c.post("/api/auth/forgot-password", json={"email": reset_email})
    check("reset: forgot-password gives the generic reply during lock",
          r.status_code == 200 and "If an account exists" in r.json().get("message", ""), str(r.status_code))
    check("reset: no new OTP created during lock", otp_count(reset_email, "password_reset") == before)

    # Round 2 on the SAME OTP: guesses 4 and 5 are allowed, guess 6 locks again
    expire_lock(reset_email, "password_reset")
    r4 = c.post("/api/auth/reset-password", json={**new_pw, "otp_code": "000004"})
    r5 = c.post("/api/auth/reset-password", json={**new_pw, "otp_code": "000005"})
    r6 = c.post("/api/auth/reset-password", json={**new_pw, "otp_code": "000006"})
    check("reset: round 2 guesses 4-5 are 400, guess 6 locks again",
          [r4.status_code, r5.status_code, r6.status_code] == [400, 400, 429],
          str([r4.status_code, r5.status_code, r6.status_code]))

    # A new OTP must NOT reset the count: guesses 7 and 8 are allowed, guess 9 locks
    expire_lock(reset_email, "password_reset")
    r = c.post("/api/auth/forgot-password", json={"email": reset_email})
    check("reset: new OTP allowed after lock expires", r.status_code == 200, str(r.status_code))
    plant_known_otp(reset_email)
    r7 = c.post("/api/auth/reset-password", json={**new_pw, "otp_code": "000007"})
    r8 = c.post("/api/auth/reset-password", json={**new_pw, "otp_code": "000008"})
    r9 = c.post("/api/auth/reset-password", json={**new_pw, "otp_code": "000009"})
    check("reset: new OTP does not reset the count (7-8 are 400, 9 locks)",
          [r7.status_code, r8.status_code, r9.status_code] == [400, 400, 429],
          str([r7.status_code, r8.status_code, r9.status_code]))

    # After the wait, the same new OTP still works
    expire_lock(reset_email, "password_reset")
    r = c.post("/api/auth/reset-password", json={**new_pw, "otp_code": CORRECT})
    check("reset: same OTP works after the wait", r.status_code == 200, f"{r.status_code} {r.text[:200]}")

finish()
