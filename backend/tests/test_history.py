"""Results history: archived courses stay downloadable after promotion, per-course
and per-group Excel exports include every student and every quiz, admin only.

    TEST_DATABASE_URL=sqlite:///./test_history.db  python -m tests.test_history
"""
import io

from openpyxl import load_workbook

from tests.helpers import TestClient, app, check, finish, class_setup, CSV_BANK
import io as _io

with TestClient(app) as c:
    st = class_setup(c, "hist", 2027, "HIS301")
    th, s1, s2, course_id = st["th"], st["s1"], st["s2"], st["course_id"]
    admin_h = st["admin_h"]

    r = c.post("/api/quizzes", headers=th, data={
        "course_id": course_id, "title": "History Quiz", "description": "bank quiz",
        "total_questions": "3",
    }, files={"question_file": ("bank.csv", _io.BytesIO(CSV_BANK), "text/csv")})
    check("create quiz", r.status_code == 201, f"{r.status_code} {r.text[:300]}")
    quiz_id = r.json()["id"]

    # Sami answers everything correctly; Sara never submits
    r = c.get(f"/api/quizzes/{quiz_id}", headers=th)
    correct_map = {q["id"]: q["correct_index"] for q in r.json()["questions"]}
    r1 = c.get(f"/api/quizzes/{quiz_id}", headers=s1)
    c.post(f"/api/quizzes/{quiz_id}/submit", headers=s1, json={"answers": [
        {"question_id": q["id"], "selected_index": correct_map[q["id"]]} for q in r1.json()["questions"]]})

    # Promote both students out of semester 1 (archives the course for the teacher)
    r = c.post("/api/users/promotion/promote", headers=admin_h, json={
        "student_ids": [st["sami_id"], st["sara_id"]], "to_semester": 2})
    check("promote both students", r.status_code == 200, f"{r.status_code} {r.text[:200]}")

    # Teacher no longer sees the course
    r = c.get("/api/courses/", headers=th)
    teacher_codes = [x["course_code"] for x in r.json()] if r.status_code == 200 else []
    check("teacher loses archived course", "HIS301" not in teacher_codes, str(teacher_codes))

    # Admin history lists it, marked archived, under semester 1
    r = c.get("/api/history/courses", headers=admin_h)
    check("history list 200", r.status_code == 200, f"{r.status_code} {r.text[:200]}")
    groups = r.json() if r.status_code == 200 else []
    found = [(g, co) for g in groups for co in g["courses"] if co["course_code"] == "HIS301"]
    check("course in history", len(found) == 1, str(groups)[:300])
    if found:
        g, co = found[0]
        check("group is semester 1", g["semester"] == 1 and g["session"] == st["session"], str(g))
        check("course archived", co["is_active"] is False, str(co))
        check("quiz counted", co["quiz_count"] == 1, str(co))

    # Per-course export: both students present, quiz score per student
    r = c.get(f"/api/history/courses/{course_id}/export", headers=admin_h)
    ok = r.status_code == 200 and "spreadsheetml" in r.headers.get("content-type", "")
    check("course export is xlsx", ok, f"{r.status_code} {r.headers.get('content-type')}")
    if ok:
        ws = load_workbook(io.BytesIO(r.content)).active
        rows = [row for row in ws.iter_rows(values_only=True)]
        header = next((row for row in rows if row and row[0] == "#"), None)
        check("header has quiz column", header is not None and "History Quiz" in header, str(header))
        body = [row for row in rows if row and isinstance(row[0], int)]
        sami = next((row for row in body if row[2] == "Sami Student"), None)
        sara = next((row for row in body if row[2] == "Sara Student"), None)
        check("Sami row present", sami is not None, str(body))
        check("Sara row present", sara is not None, str(body))
        if sami and header:
            qi = header.index("History Quiz")
            check("Sami score 3/3", sami[qi] == "3/3", str(sami))
            check("Sami 100%", sami[-1] == 100, str(sami))
        if sara and header:
            qi = header.index("History Quiz")
            check("Sara not attempted", sara[qi] == "Not attempted", str(sara))
            check("Sara possible = assigned 3, not bank 10", sara[-2] == 3, str(sara))

    # Per-group export: one sheet per subject, named after the course code
    r = c.get("/api/history/export", headers=admin_h,
              params={"session": st["session"], "semester": 1, "session_type": "morning"})
    check("group export is xlsx", r.status_code == 200 and "spreadsheetml" in r.headers.get("content-type", ""),
          f"{r.status_code}")
    if r.status_code == 200:
        wb = load_workbook(io.BytesIO(r.content))
        check("group workbook has subject sheet", "HIS301" in wb.sheetnames, str(wb.sheetnames))

    # Empty group → 404, unknown course → 404
    r = c.get("/api/history/export", headers=admin_h,
              params={"session": st["session"], "semester": 7, "session_type": "morning"})
    check("empty group 404", r.status_code == 404, str(r.status_code))
    r = c.get("/api/history/courses/does-not-exist/export", headers=admin_h)
    check("unknown course 404", r.status_code == 404, str(r.status_code))

    # Teachers and students cannot use the history endpoints
    r = c.get("/api/history/courses", headers=th)
    check("teacher denied history", r.status_code in (401, 403), str(r.status_code))
    r = c.get(f"/api/history/courses/{course_id}/export", headers=s1)
    check("student denied export", r.status_code in (401, 403), str(r.status_code))

finish()
