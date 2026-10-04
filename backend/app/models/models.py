import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float,
    DateTime, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.database.database import Base


def generate_uuid():
    return str(uuid.uuid4())


def utcnow():
    """UTC now as naive datetime (stored as naive UTC in DB columns)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Role(Base):
    __tablename__ = "roles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=utcnow)

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(String(36), ForeignKey("roles.id"), nullable=False, index=True)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    role = relationship("Role", back_populates="users")
    teacher_profile = relationship("TeacherProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    student_profile = relationship("StudentProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    taught_courses = relationship("Course", back_populates="teacher")
    otp_records = relationship("OTPVerification", back_populates="user", cascade="all, delete-orphan")
    quizzes = relationship("Quiz", back_populates="teacher")


class TeacherProfile(Base):
    __tablename__ = "teacher_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    employee_id = Column(String(50), unique=True)
    department = Column(String(100))
    qualification = Column(String(255))
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="teacher_profile")


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    student_id = Column(String(50), unique=True)
    roll_number = Column(String(50), index=True)
    department = Column(String(100))
    semester = Column(Integer)
    enrollment_year = Column(Integer)
    session = Column(String(20), index=True)
    session_type = Column(String(10), index=True, default="morning")  # morning or evening
    is_graduated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        Index(
            "uq_student_roll_scope",
            "roll_number",
            "semester",
            "session",
            "session_type",
            unique=True,
        ),
    )

    user = relationship("User", back_populates="student_profile")


class Course(Base):
    __tablename__ = "courses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    course_code = Column(String(20), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    semester = Column(Integer, index=True)
    session = Column(String(20), index=True)  # e.g. "23-27"
    session_type = Column(String(10), index=True, default="morning")  # morning or evening
    teacher_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    source_course_id = Column(String(36), ForeignKey("courses.id"), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    teacher = relationship("User", back_populates="taught_courses")
    source_course = relationship("Course", remote_side="Course.id", backref="derived_courses")
    quizzes = relationship("Quiz", back_populates="course", cascade="all, delete-orphan")


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False, index=True)
    teacher_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    time_limit = Column(Integer, nullable=True)  # minutes; null = no limit
    deadline = Column(DateTime, nullable=True)  # deadline to attempt; null = no deadline
    total_questions = Column(Integer, nullable=True)  # questions sent to each student (null = all)
    attachment_url = Column(String(500), nullable=True)
    attachment_name = Column(String(255), nullable=True)
    max_marks = Column(Integer, nullable=True)
    is_published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    course = relationship("Course", back_populates="quizzes")
    teacher = relationship("User", back_populates="quizzes")
    questions = relationship(
        "QuizQuestion",
        back_populates="quiz",
        cascade="all, delete-orphan",
        order_by="QuizQuestion.order_index",
    )
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    quiz_id = Column(String(36), ForeignKey("quizzes.id"), nullable=False, index=True)
    text = Column(Text, nullable=False)
    options = Column(Text, nullable=False)  # JSON array of options
    correct_index = Column(Integer, nullable=False)
    order_index = Column(Integer, default=0)

    quiz = relationship("Quiz", back_populates="questions")


class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    otp_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    attempts = Column(Integer, default=0)
    is_used = Column(Boolean, default=False)
    purpose = Column(String(50), default="registration", nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, index=True)

    user = relationship("User", back_populates="otp_records")



class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    quiz_id = Column(String(36), ForeignKey("quizzes.id"), nullable=False, index=True)
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    score = Column(Integer, nullable=False, default=0)
    total = Column(Integer, nullable=False, default=0)
    submission_url = Column(String(500), nullable=True)
    submission_name = Column(String(255), nullable=True)
    grade = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    grading_status = Column(String(20), default="submitted", nullable=False)
    submitted_at = Column(DateTime, default=utcnow)

    quiz = relationship("Quiz", back_populates="attempts")
    student = relationship("User")
    answers = relationship("QuizAttemptAnswer", back_populates="attempt", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("quiz_id", "student_id", name="uq_quiz_student_attempt"),
    )


class QuizAttemptAnswer(Base):
    __tablename__ = "quiz_attempt_answers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    attempt_id = Column(String(36), ForeignKey("quiz_attempts.id"), nullable=False, index=True)
    question_id = Column(String(36), ForeignKey("quiz_questions.id"), nullable=False)
    selected_index = Column(Integer, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)

    attempt = relationship("QuizAttempt", back_populates="answers")
    question = relationship("QuizQuestion")


class PromotionHistory(Base):
    __tablename__ = "promotion_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    from_semester = Column(Integer, nullable=False)
    to_semester = Column(Integer, nullable=False)
    session = Column(String(20), nullable=False)
    promoted_at = Column(DateTime, default=utcnow)
    promoted_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    student = relationship("User", foreign_keys=[student_id])
    admin = relationship("User", foreign_keys=[promoted_by])
