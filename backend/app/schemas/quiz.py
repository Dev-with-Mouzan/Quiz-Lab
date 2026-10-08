from typing import List, Optional
from pydantic import BaseModel

from app.schemas.common import UTCDateTime


class QuestionDetailOut(BaseModel):
    id: str
    text: str
    options: List[str]
    order_index: int
    # only populated for the owning teacher (hidden from students)
    correct_index: Optional[int] = None


class QuizOut(BaseModel):
    id: str
    course_id: str
    course_title: Optional[str] = None
    course_code: Optional[str] = None
    title: str
    description: Optional[str] = None
    time_limit: Optional[int] = None
    # stored as naive UTC; serialized with Z so browsers parse the correct instant
    deadline: Optional[UTCDateTime] = None
    # Number of questions sent to each student (None = all questions)
    total_questions: Optional[int] = None
    question_count: int
    max_marks: Optional[int] = None
    is_published: bool
    created_at: UTCDateTime


class QuizDetailOut(QuizOut):
    questions: List[QuestionDetailOut] = []
    # when this student first opened a timed quiz (serialized with Z suffix)
    started_at: Optional[UTCDateTime] = None


class ParsedQuestionOut(BaseModel):
    text: str
    options: List[str]
    correct: int


class ParseFileOut(BaseModel):
    questions: List[ParsedQuestionOut]
    count: int


class QuizAnswerIn(BaseModel):
    question_id: str
    selected_index: int


class QuizSubmitIn(BaseModel):
    answers: List[QuizAnswerIn]
    # set by the client's countdown auto-submit: unanswered questions allowed
    timed_out: bool = False


class QuizAnswerResultOut(BaseModel):
    question_id: str
    question_text: str
    options: List[str]
    selected_index: int
    correct_index: int
    is_correct: bool


class QuizAttemptOut(BaseModel):
    id: str
    quiz_id: str
    score: int
    total: int
    submitted_at: object
    answers: List[QuizAnswerResultOut] = []


class QuizTeacherAttemptOut(BaseModel):
    id: str
    quiz_id: str
    student_id: str
    student_name: str
    score: int
    total: int
    percentage: float
    submitted_at: object
