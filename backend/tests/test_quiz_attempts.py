"""Quiz taking: per-student question subsets, answer hiding, scoring, attempt visibility.

    TEST_DATABASE_URL=sqlite:///./test_final.db  python -m tests.test_quiz_attempts

Note: the "different subsets/orders" check is random. With 10 questions and 3 per
student it fails only if both students happen to get the same subset and order.
"""
import io

from tests.helpers import TestClient, app, check, finish, class_setup, CSV_BANK

with TestClient(app) as c:
    st = class_setup(c, "attempts", 2026, "CS201")
    th, s1, s2, course_id = st["th"], st["s1"], st["s2"], st["course_id"]

    r = c.post("/api/quizzes", headers=th, data={
        "course_id": course_id, "title": "Shuffled Quiz", "description": "bank quiz",
        "total_questions": "3",
    }, files={"question_file": ("bank.csv", io.BytesIO(CSV_BANK), "text/csv")})
    check("create quiz from file", r.status_code == 201, f"{r.status_code} {r.text[:300]}")
    quiz_id = r.json()["id"]

    # ── Students see the quiz in their list ──
    r = c.get("/api/quizzes", headers=s1)
    check("student lists quizzes", r.status_code == 200 and any(q["id"] == quiz_id for q in r.json()),
          f"{r.status_code} {len(r.json()) if r.status_code == 200 else r.text[:200]}")

    # ── Each student gets their own shuffled subset of 3 ──
    r1 = c.get(f"/api/quizzes/{quiz_id}", headers=s1)
    r2 = c.get(f"/api/quizzes/{quiz_id}", headers=s2)
    check("student1 gets 3 questions", r1.status_code == 200 and len(r1.json()["questions"]) == 3,
          f"{len(r1.json().get('questions', []))}")
    check("student2 gets 3 questions", r2.status_code == 200 and len(r2.json()["questions"]) == 3,
          f"{len(r2.json().get('questions', []))}")
    check("students cannot see answers",
          all(q["correct_index"] is None for q in r1.json()["questions"]))

    ids1 = [q["id"] for q in r1.json()["questions"]]
    ids2 = [q["id"] for q in r2.json()["questions"]]
    check("students got different subsets/orders", ids1 != ids2)

    # ── Refetch gives the SAME subset (deterministic) ──
    r1b = c.get(f"/api/quizzes/{quiz_id}", headers=s1)
    check("refetch is stable for same student",
          [q["id"] for q in r1b.json()["questions"]] == ids1)

    # ── Student1 submits all correct (teacher's full bank gives the answer key) ──
    r = c.get(f"/api/quizzes/{quiz_id}", headers=th)
    correct_map = {q["id"]: q["correct_index"] for q in r.json()["questions"]}
    answers = [{"question_id": q["id"], "selected_index": correct_map[q["id"]]}
               for q in r1.json()["questions"]]
    r = c.post(f"/api/quizzes/{quiz_id}/submit", headers=s1, json={"answers": answers})
    check("student1 submits (all correct)", r.status_code == 200 and r.json()["score"] == 3,
          f"{r.status_code} {r.text[:300]}")

    # ── Wrong answers score correctly ──
    answers2 = [{"question_id": q["id"],
                 "selected_index": (correct_map[q["id"]] + 1) % len(q["options"])}
                for q in r2.json()["questions"]]
    r = c.post(f"/api/quizzes/{quiz_id}/submit", headers=s2, json={"answers": answers2})
    check("student2 submits (all wrong)", r.status_code == 200 and r.json()["score"] == 0,
          f"{r.status_code} {r.text[:300]}")

    # ── Double submit rejected ──
    r = c.post(f"/api/quizzes/{quiz_id}/submit", headers=s1, json={"answers": answers})
    check("duplicate attempt rejected", r.status_code == 400, str(r.status_code))

    # ── Student sees own attempt ──
    r = c.get(f"/api/quizzes/{quiz_id}/attempts", headers=s1)
    check("student sees own attempt", r.status_code == 200 and r.json()["score"] == 3, r.text[:200])

    # ── Teacher sees all attempts ──
    r = c.get(f"/api/quizzes/{quiz_id}/all-attempts", headers=th)
    check("teacher sees 2 attempts", r.status_code == 200 and len(r.json()) == 2, r.text[:200])

    # ── Student cannot create quizzes ──
    r = c.post("/api/quizzes", headers=s1, data={"course_id": course_id, "title": "Nope"})
    check("student cannot create quiz", r.status_code == 403, str(r.status_code))

    # ── Teacher delete works ──
    r = c.post("/api/quizzes", headers=th, data={
        "course_id": course_id, "title": "Manual Quiz",
        "questions": '[{"text": "Pick one", "options": ["a1", "a2"], "correct": 1}]',
    })
    check("create manual quiz", r.status_code == 201, f"{r.status_code} {r.text[:200]}")
    manual_id = r.json()["id"]
    r = c.delete(f"/api/quizzes/{manual_id}", headers=th)
    check("teacher deletes quiz", r.status_code == 200, str(r.status_code))

finish()
