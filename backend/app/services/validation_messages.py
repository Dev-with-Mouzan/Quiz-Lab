"""Turn FastAPI/Pydantic request-validation errors into plain, user-facing messages.

Without this, users see raw text such as "Value error, Password must contain at
least one uppercase letter" or "Input should be a valid integer". The handler
below returns the same 422 status, but `detail` is a single readable sentence.
"""
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Friendly names for form fields. Anything not listed is derived from the field name.
FIELD_LABELS = {
    "first_name": "First name",
    "last_name": "Last name",
    "email": "Email",
    "password": "Password",
    "new_password": "New password",
    "confirm_password": "Confirm password",
    "otp_code": "OTP code",
    "roll_number": "Roll number",
    "semester": "Semester",
    "enrollment_year": "Enrollment year",
    "department": "Department",
    "session_type": "Session type",
    "session": "Session",
    "course_code": "Course code",
    "title": "Title",
    "description": "Description",
    "teacher_id": "Teacher",
    "course_id": "Course",
    "total_questions": "Number of questions",
    "time_limit": "Time limit",
    "deadline": "Deadline",
    "answers": "Answers",
    "selected_index": "Selected answer",
    "question_id": "Question",
    "student_ids": "Students",
    "to_semester": "Target semester",
}

_PYDANTIC_PREFIX = "Value error, "


def _label_for(loc) -> str | None:
    """Pick the most specific string part of the error location, e.g. ('body', 'email') -> 'Email'."""
    for part in reversed(tuple(loc)):
        if isinstance(part, str) and part not in ("body", "query", "path", "header", "cookie", "form"):
            return FIELD_LABELS.get(part, part.replace("_", " ").strip().capitalize())
    return None


def _ensure_period(text: str) -> str:
    text = text.strip()
    return text if text.endswith((".", "!", "?")) else text + "."


def _message_for(err: dict) -> str:
    label = _label_for(err.get("loc", ()))
    err_type = err.get("type", "")
    raw = str(err.get("msg", "")).strip()
    if raw.startswith(_PYDANTIC_PREFIX):
        raw = raw[len(_PYDANTIC_PREFIX):]

    if err_type == "missing":
        return f"{label or 'A field'} is required."
    if err_type in ("string_too_short",):
        return f"{label or 'This field'} is too short."
    if err_type in ("string_too_long",):
        return f"{label or 'This field'} is too long."
    if err_type in ("int_parsing", "int_type", "int_from_float"):
        return f"{label or 'This field'} must be a whole number."
    if err_type in ("float_parsing", "float_type"):
        return f"{label or 'This field'} must be a number."
    if err_type in ("greater_than", "greater_than_equal", "less_than", "less_than_equal"):
        return f"{label or 'This value'} is out of the allowed range."
    if raw.lower().startswith("value is not a valid email"):
        return "Please enter a valid email address."
    if err_type == "json_invalid" or err_type == "model_attributes_type":
        return "The request data is not in the expected format."

    # Validator messages written in app/schemas (e.g. "Password must contain ...")
    if raw and not raw.lower().startswith("input should be"):
        return _ensure_period(raw)

    return f"{label or 'This field'} is invalid."


def friendly_messages(errors: list[dict]) -> str:
    """Join unique messages from all validation errors into one readable string."""
    seen, parts = set(), []
    for err in errors:
        msg = _message_for(err)
        if msg not in seen:
            seen.add(msg)
            parts.append(msg)
    return " ".join(parts) or "Please check the information you entered."


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": friendly_messages(exc.errors())},
    )
