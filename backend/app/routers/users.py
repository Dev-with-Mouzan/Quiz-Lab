from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import require_admin
from app.dependencies.ratelimit import limiter
from app.models import User, Role, TeacherProfile, StudentProfile, Course, PromotionHistory, Quiz, QuizAttempt, QuizQuestion
from app.schemas.user import (
    UserCreate, UserUpdate, UserWithRole, PromotionRequest,
)
from app.services.auth_service import (
    create_user as create_user_service,
    get_student_by_roll_number,
)
from app.services.email_service import send_credentials_email

from app.routers.courses import _student_session_label as _session_label

router = APIRouter(prefix="/api/users", tags=["Users"])


def _get_user_or_404(db: Session, user_id) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _check_email_available(db: Session, email: str, exclude_user_id=None) -> None:
    query = db.query(User).filter(User.email == email)
    if exclude_user_id:
        query = query.filter(User.id != exclude_user_id)
    if query.first():
        raise HTTPException(status_code=400, detail="Email already registered")


def _roll_number_conflict(db: Session, profile: StudentProfile, semester: int):
    if not profile.roll_number or profile.enrollment_year is None:
        return None
    session = _session_label(profile.enrollment_year)
    session_type = profile.session_type or "morning"
    return get_student_by_roll_number(
        db,
        profile.roll_number,
        semester,
        session,
        session_type,
        exclude_user_id=profile.user_id,
    )


def _delete_user_dependencies(db: Session, user: User) -> None:
    """Hard-delete a user and every row that references them (dependency order).

    Covers quizzes/attempts, OTP records, profiles, promotion history,
    and — for teachers — their taught courses (with each course's quizzes).
    """
    from app.models import (
        OTPVerification, Quiz, QuizQuestion,
        PromotionHistory, QuizAttempt, QuizAttemptAnswer,
    )

    user_id = user.id

    # Course children for every course this user teaches (teacher case)
    taught_course_ids = [
        cid for (cid,) in db.query(Course.id).filter(Course.teacher_id == user_id).all()
    ]
    for course_id in taught_course_ids:
        quiz_ids = [q.id for q in db.query(Quiz.id).filter(Quiz.course_id == course_id).all()]
        if quiz_ids:
            db.query(QuizAttemptAnswer).filter(
                QuizAttemptAnswer.attempt_id.in_(
                    db.query(QuizAttempt.id).filter(QuizAttempt.quiz_id.in_(quiz_ids))
                )
            ).delete(synchronize_session=False)
            db.query(QuizAttempt).filter(QuizAttempt.quiz_id.in_(quiz_ids)).delete(synchronize_session=False)
        db.query(QuizQuestion).filter(
            QuizQuestion.quiz_id.in_(
                db.query(Quiz.id).filter(Quiz.course_id == course_id)
            )
        ).delete(synchronize_session=False)
        db.query(Quiz).filter(Quiz.course_id == course_id).delete()
    db.query(Course).filter(Course.teacher_id == user_id).delete()

    # Direct user references
    db.query(OTPVerification).filter(OTPVerification.user_id == user_id).delete()
    db.query(QuizQuestion).filter(
        QuizQuestion.quiz_id.in_(
            db.query(Quiz.id).filter(Quiz.teacher_id == user_id)
        )
    ).delete(synchronize_session=False)
    db.query(Quiz).filter(Quiz.teacher_id == user_id).delete()
    db.query(PromotionHistory).filter(
        (PromotionHistory.student_id == user_id) | (PromotionHistory.promoted_by == user_id)
    ).delete()
    db.query(QuizAttemptAnswer).filter(
        QuizAttemptAnswer.attempt_id.in_(
            db.query(QuizAttempt.id).filter(QuizAttempt.student_id == user_id)
        )
    ).delete(synchronize_session=False)
    db.query(QuizAttempt).filter(QuizAttempt.student_id == user_id).delete()
    db.query(TeacherProfile).filter(TeacherProfile.user_id == user_id).delete()
    db.query(StudentProfile).filter(StudentProfile.user_id == user_id).delete()


# ── Static routes (must precede dynamic /{user_id}) ───
@router.get("/", response_model=List[UserWithRole])
@router.get("", response_model=List[UserWithRole])
@limiter.limit("300/minute")
def list_users(request: Request, 
        role: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all users (admin only). Optional role filter."""
    query = db.query(User)
    if role:
        role_obj = db.query(Role).filter(Role.name == role).first()
        if role_obj:
            query = query.filter(User.role_id == role_obj.id)
    return query.offset(skip).limit(limit).all()


@router.get("/stats/dashboard")
@limiter.limit("300/minute")
def get_admin_stats(request: Request, 
        db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get admin dashboard statistics."""
    total_users = db.query(User).count()
    total_students = db.query(User).join(Role).filter(Role.name == "student").count()
    total_teachers = db.query(User).join(Role).filter(Role.name == "teacher").count()
    pending_verification = db.query(User).filter(User.is_verified == False).count()  # noqa: E712
    active_users = db.query(User).filter(User.is_active == True).count()  # noqa: E712

    return {
        "total_users": total_users,
        "total_students": total_students,
        "total_teachers": total_teachers,
        "active_users": active_users,
        "pending_verification": pending_verification,
    }


@router.get("/{user_id}/profile")
@limiter.limit("300/minute")
def get_student_profile(request: Request,
        user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Student profile: identity, current-semester quizzes, promotion history."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")

    session_label = _session_label(profile.enrollment_year) if profile.enrollment_year else None

    # Courses for the CURRENT semester only (so promoted students show zeroed data)
    student_st = profile.session_type or "morning"
    courses = db.query(Course).filter(
        Course.session == session_label,
        Course.semester == profile.semester,
        Course.session_type == student_st,
    ).all()
    course_ids = [c.id for c in courses]

    quizzes = []
    if course_ids:
        quiz_rows = db.query(Quiz).filter(Quiz.course_id.in_(course_ids)).all()
        quiz_ids = [q.id for q in quiz_rows]
        attempts = {}
        q_counts = {}
        if quiz_ids:
            attempts = {a.quiz_id: a for a in db.query(QuizAttempt).filter(
                QuizAttempt.student_id == user_id,
                QuizAttempt.quiz_id.in_(quiz_ids),
            ).all()}
            q_counts = dict(db.query(QuizQuestion.quiz_id, func.count(QuizQuestion.id)).filter(
                QuizQuestion.quiz_id.in_(quiz_ids),
            ).group_by(QuizQuestion.quiz_id).all())
        course_names = {c.id: c.title for c in courses}
        for q in quiz_rows:
            attempt = attempts.get(q.id)
            quizzes.append({
                "id": q.id,
                "title": q.title,
                "course_id": q.course_id,
                "course_name": course_names.get(q.course_id),
                "total_questions": q_counts.get(q.id, 0),
                "score": attempt.score if attempt else None,
                "total": attempt.total if attempt else None,
                "submitted_at": attempt.submitted_at.isoformat() if attempt and attempt.submitted_at else None,
                "attempted": attempt is not None,
            })

    promo_history = db.query(PromotionHistory).filter(
        PromotionHistory.student_id == user_id
    ).order_by(PromotionHistory.promoted_at.desc()).all()
    promotions = [
        {
            "id": ph.id,
            "from_semester": ph.from_semester,
            "to_semester": ph.to_semester,
            "session": ph.session,
            "promoted_at": ph.promoted_at.isoformat() if ph.promoted_at else None,
        }
        for ph in promo_history
    ]

    return {
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
        },
        "profile": {
            "student_id": profile.id,
            "roll_number": profile.roll_number,
            "department": profile.department,
            "semester": profile.semester,
            "session": session_label,
            "enrollment_year": profile.enrollment_year,
        },
        "quizzes": quizzes,
        "promotions": promotions,
    }


@limiter.limit("300/minute")
@router.get("/{user_id}/semester-progress")
def get_semester_progress(request: Request,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get full 8-semester progress for a student."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")

    session_label = _session_label(profile.enrollment_year) if profile.enrollment_year else None
    current_semester = profile.semester or 1
    student_st = profile.session_type or "morning"

    # Batch-load everything for all 8 semesters (3 queries total, not 8×(1+N))
    all_courses = db.query(Course).filter(
        Course.session == session_label,
        Course.session_type == student_st,
    ).all()
    courses_by_sem = {}
    for c in all_courses:
        courses_by_sem.setdefault(c.semester, []).append(c)

    quiz_by_course = {}
    all_course_ids = [c.id for c in all_courses]
    if all_course_ids:
        for q in db.query(Quiz).filter(Quiz.course_id.in_(all_course_ids)).all():
            quiz_by_course.setdefault(q.course_id, []).append(q)

    all_quiz_ids = [q.id for qs in quiz_by_course.values() for q in qs]
    attempts = {}
    if all_quiz_ids:
        attempts = {a.quiz_id: a for a in db.query(QuizAttempt).filter(
            QuizAttempt.student_id == user_id,
            QuizAttempt.quiz_id.in_(all_quiz_ids),
        ).all()}

    semesters = []
    for sem in range(1, 9):
        courses = courses_by_sem.get(sem, [])

        if sem < current_semester:
            status = "completed"
        elif sem == current_semester:
            status = "current"
        else:
            status = "upcoming"

        quiz_rows = [q for c in courses for q in quiz_by_course.get(c.id, [])]
        total_quizzes = len(quiz_rows)
        attempted_count = 0
        total_score = 0
        total_possible = 0
        for q in quiz_rows:
            attempt = attempts.get(q.id)
            if attempt:
                attempted_count += 1
                total_score += attempt.score
                total_possible += attempt.total

        quiz_pct = round(total_score / total_possible * 100, 1) if total_possible > 0 else None

        semesters.append({
            "semester": sem,
            "status": status,
            "courses": len(courses),
            "course_names": [c.title for c in courses],
            "total_quizzes": total_quizzes,
            "attempted_quizzes": attempted_count,
            "quiz_pct": quiz_pct,
        })

    return {
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        },
        "profile": {
            "session": session_label,
            "current_semester": current_semester,
            "department": profile.department,
            "roll_number": profile.roll_number,
        },
        "semesters": semesters,
    }


# ── Dynamic routes ────────────────────────────────────
@limiter.limit("300/minute")
@router.post("/", response_model=UserWithRole, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=UserWithRole, status_code=status.HTTP_201_CREATED)
def create_user(request: Request, 
    data: UserCreate,
    bg_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new user (admin only)."""
    if data.role_name == "student":
        raise HTTPException(status_code=400, detail="Students cannot be created from admin panel. Use the registration page instead.")
    _check_email_available(db, data.email)

    user = create_user_service(db, data.model_dump())

    # Students created by admin: auto-verify so they can login immediately
    if user.role.name == "student":
        user.is_verified = True
        db.commit()
        db.refresh(user)

    # Teachers created by admin: auto-verify so they can login immediately,
    # and email the credentials (email, password) to the teacher.
    if user.role.name == "teacher":
        user.is_verified = True
        db.commit()
        db.refresh(user)
        bg_tasks.add_task(
            send_credentials_email,
            user.email,
            f"{user.first_name} {user.last_name}",
            data.password,
        )

    return user


@limiter.limit("300/minute")
@router.put("/{user_id}", response_model=UserWithRole)
def update_user(request: Request, 
    user_id: str,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update user details (admin only)."""
    user = _get_user_or_404(db, user_id)
    _check_email_available(db, data.email, exclude_user_id=user.id)

    update_data = data.model_dump(exclude_unset=True)
    semester = update_data.pop("semester", None)

    for field, value in update_data.items():
        setattr(user, field, value)

    if semester is not None:
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
        if profile:
            if _roll_number_conflict(db, profile, semester):
                raise HTTPException(
                    status_code=400,
                    detail="Roll number already exists for this semester, session, and shift",
                )
            profile.semester = semester
        else:
            db.add(StudentProfile(user_id=user.id, semester=semester))

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Roll number already exists for this semester, session, and shift",
        ) from exc
    db.refresh(user)

    return user


@limiter.limit("300/minute")
@router.delete("/{user_id}/hard")
def hard_delete_user(request: Request, 
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Permanently delete a user (admin only — hard delete)."""
    user = _get_user_or_404(db, user_id)

    _delete_user_dependencies(db, user)
    db.delete(user)
    db.commit()
    return {"message": "User deleted permanently"}


# ── Promotion Endpoints ──────────────────────────────

@limiter.limit("300/minute")
@router.get("/promotion/sessions")
def get_promotion_sessions(request: Request, 
    session_type: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all sessions with student counts."""
    filters = [StudentProfile.enrollment_year.isnot(None)]
    if session_type:
        filters.append(StudentProfile.session_type == session_type)
    profiles = db.query(StudentProfile).filter(*filters).all()

    sessions = {}
    for p in profiles:
        label = _session_label(p.enrollment_year)
        if label not in sessions:
            sessions[label] = {"session": label, "enrollment_year": p.enrollment_year, "student_count": 0}
        sessions[label]["student_count"] += 1

    return sorted(sessions.values(), key=lambda s: s["enrollment_year"], reverse=True)


@limiter.limit("300/minute")
@router.get("/promotion/sessions/{session}/semesters")
def get_session_semesters(request: Request, 
    session: str,
    session_type: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get semester breakdown for a session — always shows all 8 semesters."""
    parts = session.split("-")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid session format")
    try:
        start_year = int(parts[0]) + 2000
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session format")

    # Current students
    profile_filters = [
        StudentProfile.enrollment_year == start_year,
        StudentProfile.semester.isnot(None),
    ]
    if session_type:
        profile_filters.append(StudentProfile.session_type == session_type)
    profiles = db.query(StudentProfile).filter(*profile_filters).all()

    semesters = {}
    for p in profiles:
        sem = p.semester
        if sem not in semesters:
            semesters[sem] = {"semester": sem, "student_count": 0, "graduated_count": 0}
        semesters[sem]["student_count"] += 1
        if p.is_graduated:
            semesters[sem]["graduated_count"] += 1

    # Students who were promoted FROM each semester (still count them in from-semester)
    promoted_query = db.query(PromotionHistory).filter(
        PromotionHistory.session == session,
    )
    if session_type:
        session_user_ids = [p.user_id for p in db.query(StudentProfile.user_id).filter(
            StudentProfile.enrollment_year == start_year,
            StudentProfile.session_type == session_type,
        ).all()]
        promoted_query = promoted_query.filter(PromotionHistory.student_id.in_(session_user_ids))
    promoted_records = promoted_query.all()
    for r in promoted_records:
        sem = r.from_semester
        if sem not in semesters:
            semesters[sem] = {"semester": sem, "student_count": 0, "graduated_count": 0}
        semesters[sem]["student_count"] += 1

    # Always return all 8 semesters
    result = []
    for sem in range(1, 9):
        if sem in semesters:
            result.append(semesters[sem])
        else:
            result.append({"semester": sem, "student_count": 0, "graduated_count": 0})
    return result


@limiter.limit("300/minute")
@router.get("/promotion/sessions/{session}/semesters/{semester}")
def get_semester_students(request: Request, 
    session: str,
    semester: int,
    session_type: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get all students in a specific session+semester, including promoted-away students."""
    parts = session.split("-")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid session format")
    try:
        start_year = int(parts[0]) + 2000
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session format")

    # Current students in this semester
    profile_filters = [
        StudentProfile.enrollment_year == start_year,
        StudentProfile.semester == semester,
    ]
    if session_type:
        profile_filters.append(StudentProfile.session_type == session_type)
    profiles = db.query(StudentProfile).filter(*profile_filters).all()

    # Students who were promoted FROM this semester (now in a higher semester)
    promoted_query = db.query(PromotionHistory).filter(
        PromotionHistory.session == session,
        PromotionHistory.from_semester == semester,
    )
    if session_type:
        session_user_ids = [p.user_id for p in db.query(StudentProfile.user_id).filter(
            StudentProfile.enrollment_year == start_year,
            StudentProfile.session_type == session_type,
        ).all()]
        promoted_query = promoted_query.filter(PromotionHistory.student_id.in_(session_user_ids))
    promoted_records = promoted_query.all()
    promoted_ids = {r.student_id for r in promoted_records}
    promoted_map = {r.student_id: r.to_semester for r in promoted_records}

    # Collect all user IDs (current + promoted)
    all_user_ids = {p.user_id for p in profiles} | promoted_ids
    profiles_by_uid = {p.user_id: p for p in profiles}

    students = []
    users_map = {u.id: u for u in db.query(User).filter(User.id.in_(list(all_user_ids))).all()} if all_user_ids else {}
    for uid in all_user_ids:
        user = users_map.get(uid)
        if not user:
            continue
        p = profiles_by_uid.get(uid)
        is_promoted = uid in promoted_ids
        students.append({
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone,
            "is_active": user.is_active,
            "student_id": p.student_id if p else None,
            "roll_number": p.roll_number if p else None,
            "semester": p.semester if p else semester,
            "enrollment_year": p.enrollment_year if p else start_year,
            "session_type": p.session_type if p else "morning",
            "promoted": is_promoted,
            "promoted_to": promoted_map.get(uid) if is_promoted else None,
            "is_graduated": p.is_graduated if p else False,
        })

    return students


@limiter.limit("300/minute")
@router.post("/promotion/promote")
def promote_students(request: Request, 
    data: PromotionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Promote students to the next semester.

    Expects: { "student_ids": ["id1", "id2", ...], "to_semester": 4 }
    """
    student_ids = data.student_ids
    to_semester = data.to_semester

    if not student_ids:
        raise HTTPException(status_code=400, detail="No students selected")
    if not to_semester or to_semester < 1 or to_semester > 8:
        raise HTTPException(status_code=400, detail="Invalid target semester")

    profiles_to_promote = []
    pending_keys = set()
    for sid in student_ids:
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == sid).first()
        if not profile or not profile.enrollment_year:
            continue

        from_semester = profile.semester
        if from_semester == to_semester:
            continue

        session_label = _session_label(profile.enrollment_year)
        session_type = profile.session_type or "morning"
        if _roll_number_conflict(db, profile, to_semester):
            raise HTTPException(
                status_code=400,
                detail="Roll number already exists for this semester, session, and shift",
            )

        key = (profile.roll_number, to_semester, session_label, session_type)
        if profile.roll_number and key in pending_keys:
            raise HTTPException(
                status_code=400,
                detail="Roll number already exists for this semester, session, and shift",
            )
        if profile.roll_number:
            pending_keys.add(key)
        profiles_to_promote.append((profile, from_semester, session_label))

    promoted = 0
    archived_semesters = set()
    for profile, from_semester, session_label in profiles_to_promote:
        db.add(PromotionHistory(
            student_id=profile.user_id,
            from_semester=from_semester,
            to_semester=to_semester,
            session=session_label,
            promoted_by=current_user.id,
        ))

        profile.semester = to_semester
        promoted += 1

        # Track which session+semesters need course archival
        archived_semesters.add((session_label, from_semester))

    # Auto-archive courses from promoted semesters
    for session_label, sem in archived_semesters:
        db.query(Course).filter(
            Course.session == session_label,
            Course.semester == sem,
            Course.is_active == True,
        ).update({"is_active": False})

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Roll number already exists for this semester, session, and shift",
        ) from exc
    return {"message": f"Promoted {promoted} students to semester {to_semester}", "count": promoted}


@limiter.limit("300/minute")
@router.post("/promotion/graduate")
def graduate_students(request: Request,
    data: PromotionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Mark students as graduated and archive all their semester courses."""
    student_ids = data.student_ids
    if not student_ids:
        raise HTTPException(status_code=400, detail="No students selected")

    graduated = 0
    archived_semesters = set()
    for sid in student_ids:
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == sid).first()
        if not profile:
            continue
        if not profile.is_graduated:
            profile.is_graduated = True
            graduated += 1
            if profile.enrollment_year:
                session_label = _session_label(profile.enrollment_year)
                archived_semesters.add((session_label, profile.semester))

    # Archive courses from graduated semesters
    for session_label, sem in archived_semesters:
        db.query(Course).filter(
            Course.session == session_label,
            Course.semester == sem,
            Course.is_active == True,
        ).update({"is_active": False})

    db.commit()
    return {"message": f"Graduated {graduated} students", "count": graduated}


@limiter.limit("300/minute")
@router.get("/promotion/history")
def get_promotion_history(request: Request, 
    session: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get promotion history, optionally filtered by session."""
    query = db.query(PromotionHistory)
    if session:
        query = query.filter(PromotionHistory.session == session)

    records = query.order_by(PromotionHistory.promoted_at.desc()).all()

    all_user_ids = set()
    for r in records:
        all_user_ids.add(r.student_id)
        all_user_ids.add(r.promoted_by)
    users_map = {u.id: u for u in db.query(User).filter(User.id.in_(all_user_ids)).all()} if all_user_ids else {}

    result = []
    for r in records:
        student = users_map.get(r.student_id)
        admin = users_map.get(r.promoted_by)
        result.append({
            "id": r.id,
            "student_id": r.student_id,
            "student_name": f"{student.first_name} {student.last_name}" if student else "Unknown",
            "from_semester": r.from_semester,
            "to_semester": r.to_semester,
            "session": r.session,
            "promoted_by": f"{admin.first_name} {admin.last_name}" if admin else "Unknown",
            "promoted_at": r.promoted_at.isoformat() if r.promoted_at else None,
        })

    return result
