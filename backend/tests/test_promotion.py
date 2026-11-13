"""Admin promotion flow: sessions, semester listings, promote, graduate, progress.

    TEST_DATABASE_URL=sqlite:///./test_final.db  python -m tests.test_promotion
"""
from tests.helpers import TestClient, app, check, finish, class_setup

with TestClient(app) as c:
    st = class_setup(c, "promo", 2030, "CS601")
    admin_h, session = st["admin_h"], st["session"]
    sami_id, sara_id = st["sami_id"], st["sara_id"]
    th, s1, s2, course_id = st["th"], st["s1"], st["s2"], st["course_id"]

    # Semester 1 quiz: Sami gets everything right (2/2), Sara everything wrong (0/2).
    # Their marks should appear in the promotion history and the profile.
    r = c.post("/api/quizzes", headers=th, data={
        "course_id": course_id, "title": "Sem 1 Quiz",
        "questions": '[{"text": "Q1", "options": ["a1", "a2"], "correct": 0},'
                     '{"text": "Q2", "options": ["a1", "a2"], "correct": 1}]',
    })
    check("create semester quiz for marks", r.status_code == 201, f"{r.status_code} {r.text[:200]}")
    quiz_id = r.json()["id"]
    correct_map = {q["id"]: q["correct_index"] for q in c.get(f"/api/quizzes/{quiz_id}", headers=th).json()["questions"]}
    for student_h, wrong in ((s1, False), (s2, True)):
        qs = c.get(f"/api/quizzes/{quiz_id}", headers=student_h).json()["questions"]
        answers = [{"question_id": q["id"],
                    "selected_index": (correct_map[q["id"]] + 1) % 2 if wrong else correct_map[q["id"]]}
                   for q in qs]
        c.post(f"/api/quizzes/{quiz_id}/submit", headers=student_h, json={"answers": answers})

    r = c.get("/api/users/promotion/sessions", params={"session_type": "morning"}, headers=admin_h)
    check("admin lists promotion sessions",
          r.status_code == 200 and any(s["session"] == session for s in r.json()),
          str(r.json())[:200])

    r = c.get(f"/api/users/promotion/sessions/{session}/semesters", params={"session_type": "morning"}, headers=admin_h)
    sem1 = next((s for s in r.json() if s["semester"] == 1), None) if r.status_code == 200 else None
    check("2 students in semester 1", sem1 is not None and sem1["student_count"] == 2, str(r.json())[:200])

    r = c.get(f"/api/users/promotion/sessions/{session}/semesters/1", params={"session_type": "morning"}, headers=admin_h)
    check("semester 1 students listed", r.status_code == 200 and len(r.json()) == 2, str(len(r.json())))

    r = c.post("/api/users/promotion/promote", json={"student_ids": [sami_id, sara_id], "to_semester": 2},
               headers=admin_h)
    check("promote 2 students to sem 2", r.status_code == 200 and r.json()["count"] == 2, r.text[:200])

    r = c.get("/api/users/promotion/history", params={"session": session}, headers=admin_h)
    check("promotion history has 2 rows", r.status_code == 200 and len(r.json()) == 2, str(r.text[:200]))
    history_marks = {h["student_id"]: h["marks"] for h in r.json()} if r.status_code == 200 else {}
    check("history shows marks: Sami 100%, Sara 0% (sem 1)",
          history_marks.get(sami_id, {}).get("quiz_pct") == 100.0
          and history_marks.get(sami_id, {}).get("total_score") == 2
          and history_marks.get(sara_id, {}).get("quiz_pct") == 0.0,
          str(history_marks)[:300])

    r = c.get(f"/api/users/{sami_id}/profile", headers=admin_h)
    d = r.json() if r.status_code == 200 else {}
    check("profile promotion row shows sem 1 marks (100%)",
          d.get("promotions", [{}])[0].get("marks", {}).get("quiz_pct") == 100.0,
          str(d.get("promotions"))[:200])
    check("profile: semester bumped, promotions kept, no LMS keys",
          d.get("profile", {}).get("semester") == 2
          and len(d.get("promotions", [])) == 1
          and "attendance" not in d and "assignments" not in d and "results" not in d,
          r.text[:200])

    r = c.get(f"/api/users/{sami_id}/semester-progress", headers=admin_h)
    d = r.json() if r.status_code == 200 else {}
    check("semester progress: sem1 completed, sem2 current",
          r.status_code == 200 and d["semesters"][0]["status"] == "completed"
          and d["semesters"][1]["status"] == "current",
          r.text[:200])

    r = c.post("/api/users/promotion/graduate", json={"student_ids": [sara_id]}, headers=admin_h)
    check("graduate 1 student", r.status_code == 200 and r.json()["count"] == 1, r.text[:200])
    r = c.get(f"/api/users/promotion/sessions/{session}/semesters/2", params={"session_type": "morning"}, headers=admin_h)
    sara_row = next((s for s in r.json() if s["id"] == sara_id), None) if r.status_code == 200 else None
    check("sara marked graduated", sara_row is not None and sara_row["is_graduated"], str(r.text[:200]))

finish()
