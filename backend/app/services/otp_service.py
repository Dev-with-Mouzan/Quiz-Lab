import secrets
import string
from datetime import timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models import OTPVerification, User, utcnow
from app.dependencies.auth import hash_password, verify_password
from app.services.email_service import send_otp_email


def generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP code."""
    return "".join(secrets.choice(string.digits) for _ in range(length))


def create_otp(db: Session, user: User, purpose: str = "registration", send_email: bool = True):
    """Create a new OTP record for a user and optionally send it via email."""
    # Carry the wrong-guess count over from the previous OTP for this purpose.
    # Otherwise requesting a new code would reset the count, and an attacker could
    # keep guessing with fresh tries.
    previous = db.query(OTPVerification).filter(
        OTPVerification.user_id == user.id,
        OTPVerification.purpose == purpose,
    ).order_by(OTPVerification.created_at.desc()).first()
    carried_attempts = previous.attempts if previous else 0

    # Invalidate any existing unused OTPs for this user with the same purpose
    db.query(OTPVerification).filter(
        OTPVerification.user_id == user.id,
        OTPVerification.is_used == False,
        OTPVerification.purpose == purpose,
    ).update({"is_used": True})
    db.flush()

    otp_code = generate_otp()
    otp_record = OTPVerification(
        user_id=user.id,
        otp_hash=hash_password(otp_code),
        expires_at=utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        attempts=carried_attempts,
        is_used=False,
        purpose=purpose,
    )
    db.add(otp_record)
    db.commit()
    db.refresh(otp_record)

    # Send OTP via email (caller can defer via BackgroundTasks)
    if send_email and user.email:
        send_otp_email(user.email, otp_code)

    return otp_record, otp_code


def verify_otp(db: Session, user: User, otp_code: str, purpose: str = "registration") -> str:
    """Verify an OTP code for a user.

    Returns "ok" (correct code), "wrong" (a counted wrong guess), or
    "invalid" (no active OTP, or it has expired; nothing is counted).
    """
    otp_record = db.query(OTPVerification).filter(
        OTPVerification.user_id == user.id,
        OTPVerification.is_used == False,
        OTPVerification.purpose == purpose,
    ).order_by(OTPVerification.created_at.desc()).first()

    if not otp_record:
        return "invalid"

    # Check expiration
    if utcnow() > otp_record.expires_at:
        otp_record.is_used = True
        db.commit()
        return "invalid"

    # Correct code: the OTP is spent and the guess count starts again
    if verify_password(otp_code, otp_record.otp_hash):
        otp_record.is_used = True
        otp_record.verified_at = utcnow()
        otp_record.attempts = 0
        user.is_verified = True
        db.commit()
        return "ok"

    # Wrong code. The OTP stays valid, so the user can try again after the lock.
    # Every OTP_MAX_ATTEMPTS wrong guesses (3, 6, 9, ...) lock OTP entry for
    # OTP_LOCKOUT_MINUTES. Each round is therefore 3 guesses, then a 5-minute wait.
    # The router checks the lock before any further guess.
    otp_record.attempts += 1
    if otp_record.attempts % settings.OTP_MAX_ATTEMPTS == 0:
        otp_record.locked_until = utcnow() + timedelta(minutes=settings.OTP_LOCKOUT_MINUTES)
    db.commit()
    return "wrong"


def get_otp_lockout_remaining(db: Session, user: User, purpose: str = "registration") -> timedelta | None:
    """Return how long the OTP lock still lasts, or None if the user is not locked."""
    now = utcnow()
    locked = db.query(OTPVerification).filter(
        OTPVerification.user_id == user.id,
        OTPVerification.purpose == purpose,
        OTPVerification.locked_until > now,
    ).order_by(OTPVerification.locked_until.desc()).first()
    return (locked.locked_until - now) if locked else None


def get_otp_status(db: Session, user: User, purpose: str = "registration") -> dict:
    """Round status for the UI: guesses left in this round and seconds until any lock ends."""
    remaining = get_otp_lockout_remaining(db, user, purpose)
    latest = db.query(OTPVerification).filter(
        OTPVerification.user_id == user.id,
        OTPVerification.purpose == purpose,
    ).order_by(OTPVerification.created_at.desc()).first()
    used_in_round = (latest.attempts % settings.OTP_MAX_ATTEMPTS) if latest else 0
    locked_seconds = int(-(-remaining.total_seconds() // 1)) if remaining else 0
    return {
        "max_attempts": settings.OTP_MAX_ATTEMPTS,
        "attempts_left": 0 if remaining else settings.OTP_MAX_ATTEMPTS - used_in_round,
        "locked_seconds": locked_seconds,
    }


def can_resend_otp(db: Session, user: User, purpose: str = "registration") -> bool:
    """Check if user can request a new OTP (cooldown check)."""
    recent = db.query(OTPVerification).filter(
        OTPVerification.user_id == user.id,
        OTPVerification.created_at >= utcnow() - timedelta(minutes=2),
        OTPVerification.purpose == purpose,
    ).first()
    return recent is None
