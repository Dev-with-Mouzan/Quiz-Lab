"""Countdown timer: start once, resume on reopen, one timer per student,
enforce the time limit, and auto-submit on timeout.

    TEST_DATABASE_URL=sqlite:///./test_final.db  python -m tests.test_timer
"""
from datetime import timedelta

from tests.helpers import TestClient, app, check, finish, class_setup, SessionLocal
from app.models import QuizTimer, utcnow

with TestClient(app) as c:
    st = class_setup(c, "timer", 2028, "CS401")
    th, s1, s2, course_id = st["th"], st["s1"], st["s2"], st["course_id"]

    r = c.post("/api/quizzes", headers=th, data={
        "course_id": course_id, "title": "Timed Quiz", "time_limit": "10",
        "questions": '[{"text": "T1", "options": ["a1", "a2"], "correct": 0},'
                     '{"text": "T2", "options": ["a1", "a2"], "correct": 1},'
                     '{"text": "T3", "options": ["a1", "a2"], "correct": 0}]',
    })
    check("create timed quiz", r.status_code == 201, f"{r.status_code} {r.text[:200]}")
    timed_id = r.json()["id"]

    # First open records the start time; re-opening resumes, not resets.
    # Timer counts are scoped to this quiz (other test files also create timers).
    r = c.get(f"/api/quizzes/{timed_id}", headers=s1)
    started = r.json().get("started_at")
    check("timed quiz returns started_at", r.status_code == 200 and started, str(started))
    db = SessionLocal()
    try:
        check("one timer row after first open",
              db.query(QuizTimer).filter(QuizTimer.quiz_id == timed_id).count() == 1)
    finally:
        db.close()
    r2 = c.get(f"/api/quizzes/{timed_id}", headers=s1)
    check("re-open resumes same countdown", r2.json().get("started_at") == started,
          f"{started} -> {r2.json().get('started_at')}")
    db = SessionLocal()
    try:
        check("re-open does not add timer rows",
              db.query(QuizTimer).filter(QuizTimer.quiz_id == timed_id).count() == 1)
    finally:
        db.close()

    # Untimed quiz records no start time
    r = c.post("/api/quizzes", headers=th, data={
        "course_id": course_id, "title": "Untimed Quiz",
        "questions": '[{"text": "U1", "options": ["a1", "a2"], "correct": 0}]',
    })
    check("create untimed quiz", r.status_code == 201, f"{r.status_code} {r.text[:200]}")
    untimed_id = r.json()["id"]
    r = c.get(f"/api/quizzes/{untimed_id}", headers=s2)
    check("untimed quiz has no started_at", r.json().get("started_at") is None,
          str(r.json().get("started_at")))

    # Second student gets their own timer
    r = c.get(f"/api/quizzes/{timed_id}", headers=s2)
    check("second student gets own timer", r.json().get("started_at") is not None)
    db = SessionLocal()
    try:
        check("two timer rows (one per student)",
              db.query(QuizTimer).filter(QuizTimer.quiz_id == timed_id).count() == 2)
        timed_detail = r.json()
    finally:
        db.close()
    t_ids = [q["id"] for q in timed_detail["questions"]]

    # Partial submit without timed_out is still rejected
    r = c.post(f"/api/quizzes/{timed_id}/submit", headers=s2,
               json={"answers": [{"question_id": t_ids[0], "selected_index": 0}]})
    check("partial submit without timed_out rejected",
          r.status_code == 400 and "all quiz questions" in r.json().get("detail", ""),
          f"{r.status_code} {r.text[:200]}")

    # timed_out auto-submit grades partial answers (unanswered = wrong)
    # pick a correct option: T1/T3 are correct at 0, T2 at 1 (shuffle reorders)
    first_q = timed_detail["questions"][0]
    first_correct = 0 if first_q["text"] in ("T1", "T3") else 1
    r = c.post(f"/api/quizzes/{timed_id}/submit", headers=s2, json={
        "answers": [{"question_id": t_ids[0], "selected_index": first_correct}],
        "timed_out": True,
    })
    body = r.json() if r.status_code == 200 else {}
    check("timed_out partial submit accepted",
          r.status_code == 200 and body.get("total") == 3 and body.get("score") == 1,
          f"{r.status_code} {r.text[:300]}")
    # every question appears in the review; unanswered have selected_index=-1
    ans = body.get("answers", [])
    unanswered = [a for a in ans if a.get("selected_index") == -1 and a.get("is_correct") is False]
    check("review includes unanswered questions",
          len(ans) == 3 and len(unanswered) == 2 and all(a.get("correct_index") is not None for a in unanswered),
          f"{r.text[:300]}")

    # Expire student1's countdown past limit + 30s grace, then submit → rejected
    db = SessionLocal()
    try:
        t1 = db.query(QuizTimer).filter(QuizTimer.quiz_id == timed_id,
                                        QuizTimer.student_id == st["sami_id"]).one()
        t1.started_at = utcnow() - timedelta(minutes=11)
        db.commit()
    finally:
        db.close()
    r = c.get(f"/api/quizzes/{timed_id}", headers=s1)
    expired_answers = [{"question_id": q["id"], "selected_index": 0}
                       for q in r.json()["questions"]]
    r = c.post(f"/api/quizzes/{timed_id}/submit", headers=s1,
               json={"answers": expired_answers})
    check("submit after time limit rejected",
          r.status_code == 400 and "Time is up" in r.json().get("detail", ""),
          f"{r.status_code} {r.text[:200]}")

finish()
