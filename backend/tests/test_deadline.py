"""Deadlines: UTC serialization, submit rejection after the deadline, and results
for absent students once the deadline has passed.

    TEST_DATABASE_URL=sqlite:///./test_final.db  python -m tests.test_deadline
"""
import io
from datetime import datetime, timedelta

from openpyxl import load_workbook

from tests.helpers import TestClient, app, check, finish, class_setup
from app.models import utcnow

with TestClient(app) as c:
    st = class_setup(c, "deadline", 2029, "CS501")
    th, s1, course_id = st["th"], st["s1"], st["course_id"]

    # ── Deadline: serialized with Z (UTC) so browsers see the real instant ──
    r = c.post("/api/quizzes", headers=th, data={
        "course_id": course_id, "title": "Future Deadline Quiz",
        "deadline": (utcnow() + timedelta(hours=1)).isoformat() + "Z",
        "questions": '[{"text": "D1", "options": ["a1", "a2"], "correct": 0}]',
    })
    check("create future-deadline quiz", r.status_code == 201, f"{r.status_code} {r.text[:200]}")
    future_id = r.json()["id"]
    r = c.get(f"/api/quizzes/{future_id}", headers=s1)
    dl = r.json().get("deadline")
    parsed = datetime.fromisoformat(dl.replace("Z", "+00:00")) if dl else None
    check("deadline has Z and is in the future",
          bool(dl) and dl.endswith("Z") and parsed.replace(tzinfo=None) > utcnow(),
          str(dl))

    r = c.post("/api/quizzes", headers=th, data={
        "course_id": course_id, "title": "Past Deadline Quiz",
        "deadline": (utcnow() - timedelta(hours=1)).isoformat() + "Z",
        "questions": '[{"text": "D2", "options": ["a1", "a2"], "correct": 0}]',
    })
    check("create past-deadline quiz", r.status_code == 201, f"{r.status_code} {r.text[:200]}")
    past_id = r.json()["id"]

    # ── Submitting after the deadline is rejected ──
    r = c.post(f"/api/quizzes/{past_id}/submit", headers=s1, json={"answers": []})
    check("submit after deadline rejected",
          r.status_code == 400 and "deadline" in r.json().get("detail", "").lower(),
          f"{r.status_code} {r.text[:200]}")

    # ── Results: after the deadline, all enrolled students appear ──
    r = c.get(f"/api/quizzes/{future_id}/all-attempts", headers=th,
              params={"include_absent": "true"})
    check("future deadline: absent students not included",
          r.status_code == 200 and len(r.json()) == 0, f"{r.status_code} {len(r.json())}")

    r = c.get(f"/api/quizzes/{past_id}/all-attempts", headers=th,
              params={"include_absent": "true"})
    rows = r.json() if r.status_code == 200 else []
    check("past deadline: every enrolled student listed",
          r.status_code == 200 and len(rows) == 2
          and all(a["attempted"] is False and a["score"] == 0 for a in rows),
          f"{r.status_code} {r.text[:300]}")

    r = c.get(f"/api/quizzes/{past_id}/all-attempts", headers=th)
    check("all-attempts default still excludes absent",
          r.status_code == 200 and len(r.json()) == 0, str(len(r.json())))

    # ── Export lists not-attempted students with a "Not attempted" status ──
    r = c.get(f"/api/quizzes/{past_id}/export", headers=th)
    ok = r.status_code == 200 and "spreadsheetml" in r.headers.get("content-type", "")
    xrows = list(load_workbook(io.BytesIO(r.content)).active.iter_rows(values_only=True)) if ok else []
    not_attempted = [row for row in xrows if row[7] == "Not attempted"]
    check("export lists not-attempted students",
          ok and len(xrows) == 8 and len(not_attempted) == 2,
          f"{r.status_code} rows={len(xrows)} not_attempted={len(not_attempted)}")

finish()
