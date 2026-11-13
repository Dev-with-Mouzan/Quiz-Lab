"""Quiz creation from question banks: CSV/DOCX parsing, manual questions, validation.

    TEST_DATABASE_URL=sqlite:///./test_final.db  python -m tests.test_quiz_import
"""
import io

from tests.helpers import (
    TestClient, app, check, finish, admin_login, create_teacher, teacher_login,
    create_course, CSV_BANK, make_docx, DOCX_MIME,
)

with TestClient(app) as c:
    admin_h = admin_login(c)
    teacher_id = create_teacher(c, admin_h, "import.teacher@gmail.com")
    course_id = create_course(c, admin_h, teacher_id, "CS101", "26-30")
    th = teacher_login(c, "import.teacher@gmail.com")

    # ── Parse-file preview: CSV question bank ──
    r = c.post("/api/quizzes/parse-file", headers=th,
               files={"file": ("bank.csv", io.BytesIO(CSV_BANK), "text/csv")})
    check("parse CSV bank", r.status_code == 200 and r.json()["count"] == 10, f"{r.status_code} {r.text[:200]}")

    # ── Parse-file preview: DOCX question bank ──
    docx_buf = make_docx([
        "1. What is the capital of Pakistan?",
        "a) Karachi",
        "b) Lahore",
        "c) Islamabad",
        "d) Peshawar",
        "Answer: c",
        "2. 5 + 7 = ?",
        "a) 10",
        "b) 12",
        "c) 13",
        "d) 11",
        "Answer: b",
    ])
    r = c.post("/api/quizzes/parse-file", headers=th,
               files={"file": ("bank.docx", docx_buf, DOCX_MIME)})
    check("parse DOCX bank", r.status_code == 200 and r.json()["count"] == 2, f"{r.status_code} {r.text[:300]}")

    # ── Create quiz from CSV bank with total_questions=3 ──
    r = c.post("/api/quizzes", headers=th, data={
        "course_id": course_id, "title": "Shuffled Quiz", "description": "bank quiz",
        "total_questions": "3",
    }, files={"question_file": ("bank.csv", io.BytesIO(CSV_BANK), "text/csv")})
    check("create quiz from file", r.status_code == 201, f"{r.status_code} {r.text[:300]}")
    quiz_id = r.json()["id"]
    check("quiz total_questions saved", r.json()["total_questions"] == 3, str(r.json()))
    check("quiz question_count = 10", r.json()["question_count"] == 10, str(r.json()["question_count"]))

    # ── Create quiz with manual questions ──
    r = c.post("/api/quizzes", headers=th, data={
        "course_id": course_id, "title": "Manual Quiz",
        "questions": '[{"text": "Pick one", "options": ["a1", "a2"], "correct": 1}]',
    })
    check("create manual quiz", r.status_code == 201, f"{r.status_code} {r.text[:200]}")

    # ── Teacher sees full bank with correct answers ──
    r = c.get(f"/api/quizzes/{quiz_id}", headers=th)
    check("teacher gets full bank", r.status_code == 200 and len(r.json()["questions"]) == 10,
          f"{len(r.json().get('questions', []))} qs")
    check("teacher sees correct answers", all(q["correct_index"] is not None for q in r.json()["questions"]))

    # ── Validation: total_questions > bank size rejected ──
    r = c.post("/api/quizzes", headers=th, data={
        "course_id": course_id, "title": "Too many", "total_questions": "99",
    }, files={"question_file": ("bank.csv", io.BytesIO(CSV_BANK), "text/csv")})
    check("total_questions > bank rejected", r.status_code == 400, str(r.status_code))

    # ── Validation: empty quiz rejected ──
    r = c.post("/api/quizzes", headers=th, data={"course_id": course_id, "title": "Empty"})
    check("empty quiz rejected", r.status_code == 400, str(r.status_code))

finish()
