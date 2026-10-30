from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database.database import get_db
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Bearer header is optional: browsers send the session cookie instead
security = HTTPBearer(auto_error=False)
ACCESS_COOKIE = "access_token"


# ── Password Hashing ──────────────────────────────────
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Token ─────────────────────────────────────────
def create_access_token(user_id: str, role_name: str, is_verified: bool) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "role": role_name,
        "is_verified": is_verified,
        "exp": expire,
        "iat": datetime.now(timezone.utc).replace(tzinfo=None),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


# ── Current User Dependency ───────────────────────────
def set_auth_cookie(response: Response, token: str) -> None:
    """Store the session token in an HttpOnly cookie (not readable by page scripts)."""
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",  # blocks cross-site POSTs, which is the CSRF protection here
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=ACCESS_COOKIE, path="/", secure=settings.COOKIE_SECURE, samesite="lax", httponly=True)


def get_any_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Authenticated, active user — email verification NOT required.

    Accepts the session cookie (browser) or a Bearer header (API clients).
    Only for endpoints an unverified user must reach (the profile call the
    frontend makes right after login). Everything else uses get_current_user.
    """
    token = credentials.credentials if credentials else request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    payload = decode_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    return user


def get_current_user(user: User = Depends(get_any_user)) -> User:
    """Authenticated, active AND email-verified user."""
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Enter the OTP sent to your email to continue.",
        )
    return user


# ── Role-Based Dependencies ───────────────────────────
def _check_role(user: User, allowed_roles: List[str]) -> User:
    """Helper to check user role."""
    if user.role is None or user.role.name not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Required roles: {', '.join(allowed_roles)}",
        )
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    return _check_role(current_user, ["admin"])


def require_teacher(current_user: User = Depends(get_current_user)) -> User:
    return _check_role(current_user, ["teacher"])
