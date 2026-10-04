import logging
from contextlib import asynccontextmanager

from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.database.database import engine, SessionLocal, Base
from app.dependencies.ratelimit import limiter
from app.models import User
from app.services.auth_service import create_default_roles, create_default_admin
from app.routers import auth, users, courses, quizzes

logger = logging.getLogger(__name__)

# Whitelist of tables and columns allowed for startup migration
_ALLOWLISTED_MIGRATIONS = {
    "users": [("phone", "VARCHAR(20)")],
    "courses": [("semester", "INTEGER"), ("session", "VARCHAR(20)"), ("session_type", "VARCHAR(20)"), ("is_active", "BOOLEAN DEFAULT 1")],
    "student_profiles": [("roll_number", "VARCHAR(50)"), ("is_graduated", "BOOLEAN DEFAULT 0"), ("session_type", "VARCHAR(10)")],
    "quizzes": [
        ("deadline", "DATETIME"),
        ("total_questions", "INTEGER"),
        ("time_limit", "INTEGER"),
    ],
}


def _get_column_names(db, table_name: str) -> set:
    """Return existing column names for a table, dialect-aware."""
    if table_name not in _ALLOWLISTED_MIGRATIONS:
        raise ValueError(f"Table '{table_name}' is not allowlisted")
    dialect = engine.dialect.name
    if dialect == "sqlite":
        rows = db.execute(
            text(f"PRAGMA table_info({table_name})")
        )
        return {row[1] for row in rows}
    rows = db.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :tbl"
        ).bindparams(tbl=table_name),
    )
    return {row[0] for row in rows}


def _add_missing_columns(db):
    """Add missing columns to existing tables using parameterized queries."""
    for table, cols in _ALLOWLISTED_MIGRATIONS.items():
        try:
            existing = _get_column_names(db, table)
        except Exception:
            logger.warning("Could not inspect columns for table '%s'; skipping.", table)
            continue
        for col_name, col_type in cols:
            if col_name not in existing:
                try:
                    db.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}")
                    )
                    db.commit()
                    logger.info("Added column %s to %s", col_name, table)
                except Exception:
                    db.rollback()


def _backfill_student_sessions(db):
    """Compute and store session label for students missing it."""
    from app.models.models import StudentProfile
    profiles = db.query(StudentProfile).filter(
        StudentProfile.session.is_(None),
        StudentProfile.enrollment_year.isnot(None),
    ).all()
    for p in profiles:
        p.session = f"{p.enrollment_year % 100:02d}-{(p.enrollment_year + 4) % 100:02d}"
    if profiles:
        db.commit()
        logger.info("Backfilled session for %d student profiles", len(profiles))


def _backfill_session_types(db):
    """Set default session_type='morning' for existing records missing it."""
    from app.models.models import StudentProfile, Course
    profiles = db.query(StudentProfile).filter(StudentProfile.session_type.is_(None)).all()
    for p in profiles:
        p.session_type = "morning"
    courses = db.query(Course).filter(Course.session_type.is_(None)).all()
    for c in courses:
        c.session_type = "morning"
    if profiles or courses:
        db.commit()
        logger.info("Backfilled session_type for %d profiles, %d courses", len(profiles), len(courses))


def _ensure_student_roll_index(db):
    try:
        db.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_student_roll_scope "
            "ON student_profiles (roll_number, semester, session, session_type)"
        ))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise RuntimeError(
            "Cannot enforce semester-scoped roll numbers: duplicate legacy rows exist"
        ) from exc


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    if not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY must be set in .env file. Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\"")
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        raise RuntimeError("ADMIN_EMAIL and ADMIN_PASSWORD must be set in .env file")

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        create_default_roles(db)
        create_default_admin(db)
        _add_missing_columns(db)
        _backfill_student_sessions(db)
        _backfill_session_types(db)
        _ensure_student_roll_index(db)
    finally:
        db.close()

    yield


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=()"
        response.headers["Cache-Control"] = "no-store"
        return response


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Role-Based Learning Management System — Color theme, Auth & Quiz features",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware — origins from config
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include routers (auth + users + courses + quizzes only)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(courses.router)
app.include_router(quizzes.router)


@app.get("/")
@limiter.limit("60/minute")
async def root(request: Request):
    return {
        "name": settings.PROJECT_NAME,
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
@limiter.limit("60/minute")
async def health(request: Request):
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
