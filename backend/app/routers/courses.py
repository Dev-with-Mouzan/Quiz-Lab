from typing import List

from fastapi import Request,  APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.models import User, Course, StudentProfile
from app.schemas.course import CourseCreate, CourseUpdate, CourseOut
from app.dependencies.ratelimit import limiter

router = APIRouter(prefix="/api/courses", tags=["Courses"])


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


@limiter.limit("30/minute")
@router.get("/", response_model=List[CourseOut])
@router.get("", response_model=List[CourseOut])
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


@limiter.limit("30/minute")
@router.post("/", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(request: Request, 
    data: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new course (admin only)."""
    existing = db.query(Course).filter(Course.course_code == data.course_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Course code already exists")

    course_data = data.model_dump(exclude_unset=True)
    course = Course(**course_data)
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@limiter.limit("30/minute")
@router.put("/{course_id}", response_model=CourseOut)
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
    for field, value in update_data.items():
        setattr(course, field, value)

    db.commit()
    db.refresh(course)
    return course


@limiter.limit("30/minute")
@router.delete("/{course_id}")
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
