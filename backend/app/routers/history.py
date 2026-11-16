"""Admin results history: every course grouped by session, semester and shift,
with per-course Excel exports (one row per student, one column per quiz)."""
import io
import re
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import require_admin
from app.dependencies.ratelimit import limiter
from app.models import (
    User, Course, Quiz, QuizQuestion, QuizAttempt, StudentProfile, PromotionHistory,
)
from app.routers.courses import _student_session_label as _session_label

router = APIRouter(prefix="/api/history", tags=["History"])

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _shift(value: Optional[str]) -> str:
    return value or "morning"


def _safe_filename(raw: str) -> str:
    return re.sub(r"[^\w\-. ]+", "_", raw)[:100]


def _teacher_name(course: Course) -> str:
    t = course.teacher
    return f"{t.first_name} {t.last_name}".strip() if t else ""


def _sheet_title(raw: str, used: set) -> str:
    """Excel sheet names: max 31 chars, no []:*?/\\ and unique."""
    base = re.sub(r"[\[\]\*\?/\\:]", "_", raw or "Course")[:28].strip() or "Course"
    title, n = base, 2
    while title.lower() in used:
        title = f"{base[:26]}_{n}"
        n += 1
    used.add(title.lower())
    return title


def _course_roster(db: Session, course: Course, attempt_student_ids: set) -> Dict[str, tuple]:
    """Students who belong to this course's class: same session and shift, and either
    currently in this semester or promoted out of it. Students who attempted a quiz
    are always included so no result is lost."""
    shift = _shift(course.session_type)
    promoted_ids = {
        sid for (sid,) in db.query(PromotionHistory.student_id).filter(
            PromotionHistory.session == course.session,
            PromotionHistory.from_semester == course.semester,
        ).all()
    }
    profiles = db.query(StudentProfile).filter(StudentProfile.enrollment_year.isnot(None)).all()
    profiles_by_uid = {p.user_id: p for p in profiles}
    ids = {
        p.user_id for p in profiles
        if _session_label(p.enrollment_year) == course.session
        and _shift(p.session_type) == shift
        and (p.semester == course.semester or p.user_id in promoted_ids)
    } | attempt_student_ids
    if not ids:
        return {}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(list(ids))).all()}
    return {uid: (users.get(uid), profiles_by_uid.get(uid)) for uid in ids if uid in users}


def _write_course_sheet(ws, db: Session, course: Course) -> None:
    quizzes = db.query(Quiz).filter(Quiz.course_id == course.id).order_by(Quiz.created_at).all()
    quiz_ids = [q.id for q in quizzes]
    question_counts = dict(
        db.query(QuizQuestion.quiz_id, func.count(QuizQuestion.id))
        .filter(QuizQuestion.quiz_id.in_(quiz_ids))
        .group_by(QuizQuestion.quiz_id).all()
    ) if quiz_ids else {}
    attempts = {}
    if quiz_ids:
        for a in db.query(QuizAttempt).filter(QuizAttempt.quiz_id.in_(quiz_ids)).all():
            attempts[(a.quiz_id, a.student_id)] = a
    attempt_student_ids = {sid for (_, sid) in attempts}
    roster = _course_roster(db, course, attempt_student_ids)

    navy = PatternFill("solid", fgColor="1F2A44")
    light = PatternFill("solid", fgColor="E9EEF6")
    band = PatternFill("solid", fgColor="F7F9FC")
    thin = Side(style="thin", color="D3DCE8")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="center")

    headers = ["#", "Roll Number", "Student"] + [q.title for q in quizzes] + ["Total Score", "Total Possible", "Percentage"]
    last_col = len(headers)
    for i, w in enumerate([6, 16, 26] + [16] * len(quizzes) + [13, 14, 12], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    shift = _shift(course.session_type).capitalize()
    info_rows = [
        (f"{course.course_code} — {course.title}", navy, Font(bold=True, size=14, color="FFFFFF"), 26),
        (f"Session {course.session} · Semester {course.semester} · {shift} shift · Teacher: {_teacher_name(course)}",
         light, Font(bold=True, size=10, color="1F2A44"), 18),
    ]
    for row_no, (text, fill, font, height) in enumerate(info_rows, 1):
        for c in range(1, last_col + 1):
            ws.cell(row=row_no, column=c).fill = fill
        cell = ws.cell(row=row_no, column=1, value=text)
        ws.merge_cells(start_row=row_no, start_column=1, end_row=row_no, end_column=last_col)
        cell.font = font
        cell.alignment = left
        ws.row_dimensions[row_no].height = height

    header_row = 4
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=c, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = navy
        cell.alignment = center
        cell.border = border
    ws.row_dimensions[header_row].height = 36

    students = sorted(
        roster.items(),
        key=lambda kv: ((kv[1][1].roll_number if kv[1][1] and kv[1][1].roll_number else "~"),
                        (kv[1][0].first_name if kv[1][0] else "")),
    )
    row = header_row + 1
    for i, (sid, (user, profile)) in enumerate(students, 1):
        name = f"{user.first_name} {user.last_name}".strip() if user else "Unknown"
        score_total = 0
        possible_total = 0
        quiz_cells = []
        for q in quizzes:
            att = attempts.get((q.id, sid))
            if att:
                quiz_cells.append(f"{att.score}/{att.total}")
                score_total += att.score
                possible_total += att.total
            else:
                quiz_cells.append("Not attempted")
                # Each student gets total_questions (or the whole bank when unset)
                possible_total += q.total_questions or question_counts.get(q.id, 0)
        pct = round(score_total / possible_total * 100, 1) if possible_total else 0
        values = [i, (profile.roll_number if profile and profile.roll_number else ""), name,
                  *quiz_cells, score_total, possible_total, pct]
        for c, v in enumerate(values, 1):
            cell = ws.cell(row=row, column=c, value=v)
            cell.border = border
            cell.alignment = left if c == 3 else center
            if i % 2 == 0:
                cell.fill = band
        pct_color = "059669" if pct >= 70 else "D97706" if pct >= 40 else "DC2626"
        ws.cell(row=row, column=last_col).font = Font(bold=True, color=pct_color)
        row += 1

    if not students:
        ws.cell(row=row, column=1, value="No students found for this class.").font = Font(italic=True, color="475569")
    ws.freeze_panes = ws.cell(row=header_row + 1, column=4).coordinate


def _xlsx_response(wb: Workbook, filename: str) -> Response:
    buf = io.BytesIO()
    wb.save(buf)
    return Response(
        content=buf.getvalue(),
        media_type=XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{_safe_filename(filename)}"'},
    )


@router.get("/courses")
@limiter.limit("300/minute")
def list_history_courses(request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """All courses (active and archived) grouped by session, semester and shift."""
    courses = db.query(Course).all()
    quiz_counts = dict(db.query(Quiz.course_id, func.count(Quiz.id)).group_by(Quiz.course_id).all())
    groups: Dict[tuple, dict] = {}
    for c in courses:
        key = (c.session or "", c.semester or 0, _shift(c.session_type))
        if key not in groups:
            groups[key] = {
                "session": c.session,
                "semester": c.semester,
                "session_type": _shift(c.session_type),
                "courses": [],
            }
        groups[key]["courses"].append({
            "id": c.id,
            "course_code": c.course_code,
            "title": c.title,
            "teacher_name": _teacher_name(c),
            "is_active": bool(c.is_active),
            "quiz_count": quiz_counts.get(c.id, 0),
        })
    result = sorted(groups.values(), key=lambda g: (g["session"] or "", g["semester"] or 0), reverse=True)
    for g in result:
        g["courses"].sort(key=lambda c: c["course_code"])
    return result


@router.get("/courses/{course_id}/export")
@limiter.limit("300/minute")
def export_course_history(request: Request,
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Excel results for one course: one row per student, one column per quiz."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    wb = Workbook()
    ws = wb.active
    ws.title = _sheet_title(course.course_code, set())
    _write_course_sheet(ws, db, course)
    filename = f"{course.course_code}_S{course.semester}_{course.session}_{_shift(course.session_type)}_results.xlsx"
    return _xlsx_response(wb, filename)


@router.get("/export")
@limiter.limit("300/minute")
def export_group_history(request: Request,
    session: str = Query(...),
    semester: int = Query(...),
    session_type: str = Query("morning"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Excel workbook for a whole session + semester + shift: one sheet per course."""
    courses = db.query(Course).filter(
        Course.session == session,
        Course.semester == semester,
    ).order_by(Course.course_code).all()
    courses = [c for c in courses if _shift(c.session_type) == _shift(session_type)]
    if not courses:
        raise HTTPException(status_code=404, detail="No courses found for this group")
    wb = Workbook()
    used: set = set()
    for idx, course in enumerate(courses):
        ws = wb.active if idx == 0 else wb.create_sheet()
        ws.title = _sheet_title(course.course_code, used)
        _write_course_sheet(ws, db, course)
    filename = f"Results_S{semester}_{session}_{_shift(session_type)}.xlsx"
    return _xlsx_response(wb, filename)
