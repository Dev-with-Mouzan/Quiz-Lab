import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import UTCDateTime


# ── Role ──────────────────────────────────────────────
class RoleOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


# ── User Base ─────────────────────────────────────────
class UserBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr


class UserCreate(UserBase):
    password: str
    role_name: str  # "admin", "teacher", "student"
    employee_id: Optional[str] = None
    department: Optional[str] = None
    qualification: Optional[str] = None
    student_id: Optional[str] = None
    semester: Optional[int] = None
    enrollment_year: Optional[int] = None
    session_type: Optional[str] = "morning"  # morning or evening

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain an uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain a lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain a digit")
        return v


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    semester: Optional[int] = None


class UserOut(UserBase):
    id: str
    role_id: str
    is_verified: bool
    is_active: bool
    created_at: UTCDateTime
    updated_at: UTCDateTime

    class Config:
        from_attributes = True


# ── Student Profile ───────────────────────────────────
class StudentProfileOut(BaseModel):
    id: str
    user_id: str
    student_id: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None
    enrollment_year: Optional[int] = None
    session: Optional[str] = None
    session_type: Optional[str] = "morning"
    roll_number: Optional[str] = None

    class Config:
        from_attributes = True


class UserWithRole(UserOut):
    role: RoleOut
    student_profile: Optional[StudentProfileOut] = None


class PromotionRequest(BaseModel):
    student_ids: list[str]
    to_semester: int | None = Field(None, ge=1, le=8)
