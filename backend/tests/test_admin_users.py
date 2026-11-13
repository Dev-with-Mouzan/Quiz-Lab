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

    # ── No-trailing-slash variants (Vercel normalizes paths; both must match) ──
    r = c.get("/api/users", headers=admin_h)
    check("list users without trailing slash", r.status_code == 200, str(r.status_code))
    r = c.get("/api/courses", headers=admin_h)
    check("list courses without trailing slash", r.status_code == 200, str(r.status_code))

finish()
