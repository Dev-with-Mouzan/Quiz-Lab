"""Admin user management: dashboard stats, user and course listings, hard delete,
and path normalization (with and without trailing slash).

    TEST_DATABASE_URL=sqlite:///./test_final.db  python -m tests.test_admin_users
"""
from tests.helpers import TestClient, app, check, finish, class_setup, register_student, user_id

with TestClient(app) as c:
    st = class_setup(c, "admin", 2031, "CS701")
    admin_h = st["admin_h"]

    # ── Admin stats endpoint (used by admin dashboard). The database is shared
    # with other test files, so check the minimum rather than an exact count.
    r = c.get("/api/users/stats/dashboard", headers=admin_h)
    check("admin stats", r.status_code == 200 and r.json()["total_students"] >= 2, r.text[:200])

    # ── Admin lists users + courses (checks this file's records are present) ──
    r = c.get("/api/users/", headers=admin_h)
    user_ids = [u["id"] for u in r.json()] if r.status_code == 200 else []
    check("admin lists users",
          r.status_code == 200 and all(uid in user_ids for uid in (st["teacher_id"], st["sami_id"], st["sara_id"])),
          str(len(user_ids)))
    r = c.get("/api/courses/", headers=admin_h)
    course_ids = [co["id"] for co in r.json()] if r.status_code == 200 else []
    check("admin lists courses", r.status_code == 200 and st["course_id"] in course_ids, str(len(course_ids)))

    # ── Admin hard-deletes a throwaway user (exercises cascade cleanup) ──
    register_student(c, "Temp", "Delete", "admin.tempdel@gmail.com", "31-ADM-99", enrollment_year=2031)
    temp_id = user_id("admin.tempdel@gmail.com")
    r = c.delete(f"/api/users/{temp_id}/hard", headers=admin_h)
    check("admin hard-deletes user", r.status_code == 200, r.text[:200])
    r = c.get("/api/users/", headers=admin_h)
    check("hard-deleted user gone", r.status_code == 200 and temp_id not in [u["id"] for u in r.json()],
          str(len(r.json())))

    # ── Admin changes a student's semester ──
    sami_id, sara_id = st["sami_id"], st["sara_id"]
    base = {"first_name": "Sami", "last_name": "Student", "email": "admin.sami@gmail.com",
            "is_active": True, "is_verified": True}
    r = c.put(f"/api/users/{sami_id}", headers=admin_h, json={**base, "email": "admin.sami@gmail.com", "semester": 2})
    check("admin changes a student's semester", r.status_code == 200, f"{r.status_code} {r.text[:200]}")

    # Sara is still in semester 1, so Sami moving to semester 1 again is fine,
    # but a roll-number clash in the target semester must give a clear reason
    dup_roll = c.post("/api/auth/register", json={
        "first_name": "Dup", "last_name": "Roll", "email": "admin.dup@gmail.com",
        "password": "Student@123", "confirm_password": "Student@123", "roll_number": "31-ADMIN-01",
        "semester": 3, "enrollment_year": 2031, "department": "CS", "session_type": "morning",
    })
    check("setup: a student with Sami's roll number in semester 3", dup_roll.status_code == 201, dup_roll.text[:150])
    r = c.put(f"/api/users/{sami_id}", headers=admin_h, json={**base, "semester": 3})
    check("semester change with a roll clash names the other student",
          r.status_code == 400 and "Dup Roll" in r.json().get("detail", "") and "31-ADMIN-01" in r.json().get("detail", ""),
          r.text[:250])

    # ── No-trailing-slash variants (Vercel normalizes paths; both must match) ──
    r = c.get("/api/users", headers=admin_h)
    check("list users without trailing slash", r.status_code == 200, str(r.status_code))
    r = c.get("/api/courses", headers=admin_h)
    check("list courses without trailing slash", r.status_code == 200, str(r.status_code))

finish()
