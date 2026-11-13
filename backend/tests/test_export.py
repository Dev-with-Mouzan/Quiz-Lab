"""Results export: the teacher downloads the xlsx results sheet, students cannot.

    TEST_DATABASE_URL=sqlite:///./test_final.db  python -m tests.test_export
"""
import io

from openpyxl import load_workbook

from tests.helpers import TestClient, app, check, finish, class_setup, CSV_BANK

with TestClient(app) as c:
    st = class_setup(c, "export", 2027, "CS301")
    th, s1, s2, course_id = st["th"], st["s1"], st["s2"], st["course_id"]

    r = c.post("/api/quizzes", headers=th, data={
        "course_id": course_id, "title": "Export Quiz", "description": "bank quiz",
        "total_questions": "3",
    }, files={"question_file": ("bank.csv", io.BytesIO(CSV_BANK), "text/csv")})
    check("create export quiz", r.status_code == 201, f"{r.status_code} {r.text[:300]}")
    quiz_id = r.json()["id"]

    # Two attempts: Sami all correct (3/3), Sara all wrong (0/3)
    r = c.get(f"/api/quizzes/{quiz_id}", headers=th)
    correct_map = {q["id"]: q["correct_index"] for q in r.json()["questions"]}
    r1 = c.get(f"/api/quizzes/{quiz_id}", headers=s1)
    r2 = c.get(f"/api/quizzes/{quiz_id}", headers=s2)
    c.post(f"/api/quizzes/{quiz_id}/submit", headers=s1, json={"answers": [
        {"question_id": q["id"], "selected_index": correct_map[q["id"]]} for q in r1.json()["questions"]]})
    c.post(f"/api/quizzes/{quiz_id}/submit", headers=s2, json={"answers": [
        {"question_id": q["id"], "selected_index": (correct_map[q["id"]] + 1) % len(q["options"])}
        for q in r2.json()["questions"]]})

    # ── Teacher exports quiz results as Excel ──
    r = c.get(f"/api/quizzes/{quiz_id}/export", headers=th)
    rows, ok, styled = [], r.status_code == 200 and "spreadsheetml" in r.headers.get("content-type", ""), False
    if ok:
        ws = load_workbook(io.BytesIO(r.content)).active
        rows = list(ws.iter_rows(values_only=True))
        styled = bool(ws["A2"].font.bold) and str(ws["A6"].fill.fgColor.rgb).endswith("1F2A44")
    # 5 styled header rows + 1 column-header row + 2 attempt rows
    scores = sorted([rows[6][4], rows[7][4]]) if len(rows) >= 8 else []
    check("teacher exports xlsx results",
          ok and styled and len(rows) == 8 and rows[5][0] == "#" and scores == [0, 3],
          f"{r.status_code} rows={len(rows)}")

    # ── Student cannot export ──
    r = c.get(f"/api/quizzes/{quiz_id}/export", headers=s1)
    check("student cannot export", r.status_code == 403, str(r.status_code))

finish()
