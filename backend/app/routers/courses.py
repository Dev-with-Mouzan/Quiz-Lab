from typing import List

from fastapi import Request,  APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.models import User, Role, Course, StudentProfile
from app.schemas.course import CourseCreate, CourseUpdate, CourseOut
from app.dependencies.ratelimit import limiter

router = APIRouter(prefix="/api/courses", tags=["Courses"])


def _require_teacher_account(db: Session, teacher_id) -> None:
    """A course can only be owned by an existing teacher account."""
    is_teacher = (
        teacher_id is not None
        and db.query(User.id).join(Role, Role.id == User.role_id)
        .filter(User.id == teacher_id, Role.name == "teacher")
        .first() is not None
    )
    if not is_teacher:
        raise HTTPException(status_code=400, detail="teacher_id must belong to a teacher account")


def _student_session_label(enrollment_year: int) -> str:
    """Compute session label like '23-27' from enrollment year."""
    return f"{enrollment_year % 100:02d}-{(enrollment_year + 4) % 100:02d}"


def student_has_access(db: Session, user: User, course: Course, include_inactive: bool = False) -> bool:
    """Check if a student can access a course — same session, same session_type, semester <= current, active."""
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    if not profile or not profile.enrollment_year or not profile.semester:
        return False
    if not course.session or not course.semester:
        return False
    student_session = _student_session_label(profile.enrollment_year)
    # Check session_type match (morning/evening)
    student_st = profile.session_type or "morning"
    course_st = course.session_type or "morning"
    return course.session == student_session and student_st == course_st and course.semester <= profile.semester and (course.is_active or include_inactive)


def get_teacher_course_ids(db: Session, teacher_id: str, include_inactive: bool = False) -> List[str]:
    """Get course IDs a teacher should see. Active courses only unless include_inactive."""
    q = db.query(Course.id).filter(Course.teacher_id == teacher_id)
    if not include_inactive:
        q = q.filter(Course.is_active == True)
    return [c.id for c in q.all()]


def get_student_courses(db: Session, user: User) -> List[Course]:
    """Get all courses a student has access to — same session, same session_type, semester <= current, active only."""
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    if not profile or not profile.enrollment_year or not profile.semester:
        return []
    student_session = _student_session_label(profile.enrollment_year)
    student_st = profile.session_type or "morning"
    return db.query(Course).filter(
        Course.session == student_session,
        Course.session_type == student_st,
        Course.semester <= profile.semester,
        Course.is_active == True,
    ).all()


def get_course_students(db: Session, course: Course) -> List[User]:
    """Active students enrolled in a course (mirrors student_has_access rules)."""
    if not course.session or not course.semester:
        return []
    session_type = course.session_type or "morning"
    rows = (db.query(StudentProfile, User)
            .join(User, User.id == StudentProfile.user_id)
            .filter(User.is_active == True)  # noqa: E712
            .all())
    return [
        user for profile, user in rows
        if profile.enrollment_year and profile.semester
        and _student_session_label(profile.enrollment_year) == course.session
        and (profile.session_type or "morning") == session_type
        and course.semester <= profile.semester
    ]


@router.get("/", response_model=List[CourseOut])
@router.get("", response_model=List[CourseOut])
@limiter.limit("300/minute")
def list_courses(request: Request, 
    skip: int = 0,
    limit: int = 100,
    is_active: bool = None,
    session_type: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List courses based on role. Optional is_active and session_type filter."""
    role = current_user.role.name

    if role == "admin":
        q = db.query(Course)
        if is_active is not None:
            q = q.filter(Course.is_active == is_active)
        if session_type:
            q = q.filter(Course.session_type == session_type)
        courses = q.offset(skip).limit(limit).all()
    elif role == "teacher":
        q = db.query(Course).filter(
            Course.teacher_id == current_user.id,
            Course.is_active == True,
        )
        if session_type:
            q = q.filter(Course.session_type == session_type)
        courses = q.offset(skip).limit(limit).all()
    else:  # student
        courses = get_student_courses(db, current_user)

    return courses


@router.post("/", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("300/minute")
def create_course(request: Request, 
    data: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new course (admin only)."""
    existing = db.query(Course).filter(Course.course_code == data.course_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Course code already exists")
    _require_teacher_account(db, data.teacher_id)

    course_data = data.model_dump(exclude_unset=True)
    course = Course(**course_data)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.put("/{course_id}", response_model=CourseOut)
@limiter.limit("300/minute")
def update_course(request: Request, 
    course_id: str,
    data: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update course (admin only)."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    update_data = data.model_dump(exclude_unset=True)
    if "teacher_id" in update_data:
        _require_teacher_account(db, update_data["teacher_id"])
    for field, value in update_data.items():
        setattr(course, field, value)

    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}")
@limiter.limit("300/minute")
def delete_course(request: Request, 
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete course (admin only)."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    db.delete(course)
    db.commit()
    return {"message": "Course deleted successfully"}
