from typing import Optional
from pydantic import BaseModel

from app.schemas.common import UTCDateTime


class CourseCreate(BaseModel):
    course_code: str
    title: str
    description: str
    semester: int
    session: str
    session_type: str = "morning"  # morning or evening
    teacher_id: str


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    semester: Optional[int] = None
    session: Optional[str] = None
    session_type: Optional[str] = None  # morning or evening
    teacher_id: Optional[str] = None
    is_active: Optional[bool] = None


class CourseOut(BaseModel):
    id: str
    course_code: str
    title: str
    description: Optional[str] = None
    semester: Optional[int] = None
    session: Optional[str] = None
    session_type: Optional[str] = "morning"
    teacher_id: str
    source_course_id: Optional[str] = None
    is_active: bool
    created_at: UTCDateTime

    class Config:
        from_attributes = True


