from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from slowapi.util import get_remote_address
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import (
    create_access_token, get_any_user, hash_password,
    set_auth_cookie, clear_auth_cookie,
)
from app.dependencies.ratelimit import limiter
from app.models import User
from app.schemas.auth import (
    RegisterRequest, LoginRequest, TokenResponse,
    OTPVerifyRequest, OTPResendRequest,
    PasswordResetRequest, PasswordResetConfirm,
    MessageResponse, RegisterResponse,
)
from app.services.auth_service import (
    get_user_by_email, create_user, authenticate_user, update_password,
    get_student_by_roll_number,
)
from app.routers.courses import _student_session_label
from app.services.otp_service import (
    create_otp, verify_otp, can_resend_otp
)
from app.services.email_service import send_otp_email

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# In-memory failed login tracking (resets on server restart).
# Keyed by email AND client IP, so one attacker cannot lock a victim out
# from every network.
failed_logins = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
def register(request: Request, data: RegisterRequest, bg_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Register a new student account (teachers are created by admin only)."""
    existing = get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    session_type = data.session_type if data.session_type in ("morning", "evening") else "morning"
    roll_existing = get_student_by_roll_number(
        db,
        data.roll_number,
        data.semester,
        _student_session_label(data.enrollment_year),
        session_type,
    )
    if roll_existing:
        raise HTTPException(
            status_code=400,
            detail="Roll number already exists for this semester, session, and shift",
        )

    user_data = data.model_dump()
    user_data["role_name"] = "student"
    try:
        user = create_user(db, user_data)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Roll number already exists for this semester, session, and shift",
        ) from exc

    # Generate OTP for verification (defer email to background)
    otp_record, otp_code = create_otp(db, user, purpose="registration", send_email=False)
    bg_tasks.add_task(send_otp_email, user.email, otp_code)

    # Don't auto-login — let the user verify OTP first
    return RegisterResponse(
        message="Registration successful. Please verify your OTP.",
        email=data.email,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("120/minute")
def login(request: Request, data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Login with email and password."""
    # Check account lockout
    email = data.email.lower()
    lock_key = f"{email}|{get_remote_address(request)}"
    if lock_key in failed_logins:
        info = failed_logins[lock_key]
        if info["count"] >= MAX_FAILED_ATTEMPTS:
            if datetime.now(timezone.utc) < info["locked_until"]:
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Account temporarily locked due to too many failed login attempts",
                )
            else:
                failed_logins.pop(lock_key, None)

    user = authenticate_user(db, email, data.password)
    if not user:
        # Track failed attempt
        if lock_key in failed_logins:
            failed_logins[lock_key]["count"] += 1
            failed_logins[lock_key]["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
        else:
            failed_logins[lock_key] = {
                "count": 1,
                "locked_until": datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES),
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Clear failed attempts on successful login
    failed_logins.pop(lock_key, None)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    role = user.role.name
    token = create_access_token(user.id, role, user.is_verified)
    set_auth_cookie(response, token)

    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        role=role,
        is_verified=user.is_verified,
    )


@router.post("/verify-otp", response_model=TokenResponse)
@limiter.limit("60/minute")
def verify_otp_code(request: Request, data: OTPVerifyRequest, response: Response, db: Session = Depends(get_db)):
    """Verify OTP code for account activation and return a login token."""
    user = get_user_by_email(db, data.email)
    if not user:
        # Same response as a wrong code, so account existence is not revealed
        raise HTTPException(status_code=400, detail="Invalid or expired OTP code")

    # No token is issued without a valid OTP. (An already-verified account used
    # to receive a login token here with no code at all.)
    if user.is_verified:
        raise HTTPException(status_code=400, detail="This account is already verified. Please sign in.")

    success = verify_otp(db, user, data.otp_code, purpose="registration")
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP code",
        )

    # Log the user in: session cookie plus the token in the body for API clients
    role = user.role.name
    token = create_access_token(user.id, role, True)
    set_auth_cookie(response, token)
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        role=role,
        is_verified=True,
    )


@router.post("/resend-otp", response_model=MessageResponse)
@limiter.limit("20/minute")
def resend_otp(request: Request, data: OTPResendRequest, bg_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Resend OTP code."""
    user = get_user_by_email(db, data.email)
    if not user:
        return MessageResponse(message="If an account exists, an OTP has been sent")

    if user.is_verified:
        return MessageResponse(message="Account already verified")

    if not can_resend_otp(db, user, purpose="registration"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Please wait before requesting a new OTP",
        )

    otp_record, otp_code = create_otp(db, user, purpose="registration", send_email=False)
    bg_tasks.add_task(send_otp_email, user.email, otp_code)
    return MessageResponse(message="OTP sent successfully")


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("20/minute")
def forgot_password(request: Request, data: PasswordResetRequest, bg_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Request password reset via OTP sent to email."""
    user = get_user_by_email(db, data.email)
    if not user:
        # Generic answer: do not reveal which emails have accounts
        return MessageResponse(message="If an account exists, an OTP has been sent")

    otp_record, otp_code = create_otp(db, user, purpose="password_reset", send_email=False)
    bg_tasks.add_task(send_otp_email, user.email, otp_code, "password_reset")
    return MessageResponse(message="If an account exists, an OTP has been sent")


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("20/minute")
def reset_password(request: Request, data: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Reset password using OTP."""
    user = get_user_by_email(db, data.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP code",
        )

    success = verify_otp(db, user, data.otp_code, purpose="password_reset")
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP code",
        )

    update_password(db, user, data.new_password)
    return MessageResponse(message="Password reset successfully")


@router.get("/me")
@limiter.limit("300/minute")
def get_me(request: Request, current_user: User = Depends(get_any_user), db: Session = Depends(get_db)):
    """Get current user profile."""
    from app.models import StudentProfile
    semester = None
    session_type = None
    is_graduated = False
    if current_user.role.name == "student":
        profile = db.query(StudentProfile).filter(
            StudentProfile.user_id == current_user.id
        ).first()
        semester = profile.semester if profile else None
        session_type = profile.session_type if profile else None
        is_graduated = bool(profile.is_graduated) if profile else False
    return {
        "id": str(current_user.id),
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email": current_user.email,
        "role": current_user.role.name,
        "is_verified": current_user.is_verified,
        "is_active": current_user.is_active,
        "semester": semester,
        "session_type": session_type,
        "is_graduated": is_graduated,
    }


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response):
    """Clear the session cookie. Public on purpose: clearing a cookie needs no login."""
    clear_auth_cookie(response)
    return MessageResponse(message="Logged out")
