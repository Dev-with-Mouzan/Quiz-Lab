"""Teacher AI settings (provider, model, own API key) and AI question drafting."""
import re
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.dependencies.auth import require_teacher
from app.dependencies.ratelimit import limiter
from app.models import TeacherProfile, User
from app.services.ai_quiz import (
    AIError, MODEL_PATTERN, PROVIDERS, decrypt_api_key, encrypt_api_key,
    generate_questions, key_hint,
)
from app.services.document_text import MAX_EXTRACTED_CHARS, extract_text
from app.services.question_bank import QuestionParseError

router = APIRouter(prefix="/api/ai", tags=["AI"])

NOT_CONFIGURED = "Set up your AI provider and API key in your profile first."
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class AISettingsIn(BaseModel):
    provider: Literal["openai", "deepseek", "gemini"]
    model: str = Field(min_length=1, max_length=100)
    # Empty or missing keeps the saved key. A new value replaces it.
    api_key: Optional[str] = Field(default=None, max_length=300)

    @field_validator("model")
    @classmethod
    def check_model(cls, v: str) -> str:
        v = v.strip()
        if not MODEL_PATTERN.match(v):
            raise ValueError("Model name may contain only letters, digits, '.', '_' and '-'")
        return v

    @field_validator("api_key")
    @classmethod
    def strip_key(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


class AIGenerateIn(BaseModel):
    topic: str = Field(min_length=3, max_length=200)
    count: int = Field(ge=1, le=30)
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    language: Literal["English", "Urdu", "Roman Urdu"] = "English"
    notes: str = Field(default="", max_length=6000)


def _provider_catalog() -> list[dict]:
    return [{"id": pid, "name": p["name"], "models": p["models"]} for pid, p in PROVIDERS.items()]


def _get_or_create_profile(db: Session, user: User) -> TeacherProfile:
    profile = db.query(TeacherProfile).filter(TeacherProfile.user_id == user.id).first()
    if not profile:
        profile = TeacherProfile(user_id=user.id)
        db.add(profile)
    return profile


def _usable_credentials(profile: Optional[TeacherProfile]) -> tuple[str, str, str]:
    """Return (provider, model, api_key) or raise a friendly error."""
    if not profile or not profile.ai_provider or not profile.ai_model or not profile.ai_api_key_enc:
        raise HTTPException(status_code=400, detail=NOT_CONFIGURED)
    api_key = decrypt_api_key(profile.ai_api_key_enc)
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="The saved API key can no longer be read. Enter it again in your profile.",
        )
    return profile.ai_provider, profile.ai_model, api_key


@router.get("/settings")
@limiter.limit("60/minute")
def get_ai_settings(request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    """The teacher's AI settings. The API key itself is never returned, only a hint."""
    profile = db.query(TeacherProfile).filter(TeacherProfile.user_id == current_user.id).first()
    return {
        "provider": profile.ai_provider if profile else None,
        "model": profile.ai_model if profile else None,
        "has_key": bool(profile and profile.ai_api_key_enc),
        "key_hint": profile.ai_key_hint if profile and profile.ai_api_key_enc else None,
        "providers": _provider_catalog(),
    }


@router.put("/settings")
@limiter.limit("30/minute")
def save_ai_settings(request: Request,
    data: AISettingsIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    """Save provider, model and (optionally) a new API key."""
    profile = _get_or_create_profile(db, current_user)
    has_saved_key = bool(profile.ai_api_key_enc)

    if data.api_key is None and has_saved_key and profile.ai_provider != data.provider:
        # Keys are provider-specific, so a key for one provider can't be reused for another
        raise HTTPException(status_code=400, detail="Enter the API key for the newly selected provider.")

    if data.api_key is not None:
        profile.ai_api_key_enc = encrypt_api_key(data.api_key)
        profile.ai_key_hint = key_hint(data.api_key)

    profile.ai_provider = data.provider
    profile.ai_model = data.model
    db.commit()
    return {"message": "AI settings saved", "has_key": bool(profile.ai_api_key_enc)}


@router.delete("/settings/key")
@limiter.limit("30/minute")
def remove_ai_key(request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    profile = db.query(TeacherProfile).filter(TeacherProfile.user_id == current_user.id).first()
    if profile:
        profile.ai_api_key_enc = None
        profile.ai_key_hint = None
        db.commit()
    return {"message": "API key removed"}


@router.post("/settings/test")
@limiter.limit("5/minute")
def test_ai_settings(request: Request,
    data: AISettingsIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    """Test the provider, model and key shown on screen (nothing is saved).

    A typed key is used as is. Without one, the saved key is used only when the
    provider is the one it was saved for.
    """
    profile = db.query(TeacherProfile).filter(TeacherProfile.user_id == current_user.id).first()
    if data.api_key:
        api_key = data.api_key
    elif profile and profile.ai_api_key_enc and profile.ai_provider == data.provider:
        api_key = decrypt_api_key(profile.ai_api_key_enc)
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="The saved API key can no longer be read. Enter it again in your profile.",
            )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Enter an API key for {PROVIDERS[data.provider]['name']} to test it.",
        )
    provider, model = data.provider, data.model
    try:
        generate_questions(provider, model, api_key, topic="basic arithmetic",
                           count=1, difficulty="easy", language="English")
    except AIError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": f"Connection works. {PROVIDERS[provider]['name']} accepted this key and model ({model})."}


def _run_generation(db: Session, user: User, *, topic: str, count: int, difficulty: str,
                    language: str, notes: str) -> dict:
    profile = db.query(TeacherProfile).filter(TeacherProfile.user_id == user.id).first()
    provider, model, api_key = _usable_credentials(profile)
    try:
        result = generate_questions(
            provider, model, api_key,
            topic=topic, count=count, difficulty=difficulty,
            language=language, notes=notes,
        )
    except AIError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {**result, "provider": provider, "model": model}


@router.post("/generate-questions")
@limiter.limit("10/minute")
def generate_ai_questions(request: Request,
    data: AIGenerateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    """Return draft questions. Nothing is saved; the teacher reviews them first."""
    return _run_generation(db, current_user, topic=data.topic, count=data.count,
                           difficulty=data.difficulty, language=data.language, notes=data.notes)


@router.post("/generate-from-file")
@limiter.limit("5/minute")
def generate_ai_questions_from_file(request: Request,
    file: UploadFile = File(...),
    count: int = Form(..., ge=1, le=30),
    difficulty: Literal["easy", "medium", "hard"] = Form("medium"),
    language: Literal["English", "Urdu", "Roman Urdu"] = Form("English"),
    topic: str = Form("", max_length=200),
    notes: str = Form("", max_length=6000),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    """Draft questions from an uploaded PDF, DOCX or PPTX (slides or notes).

    The extracted text is reference material only. Nothing is saved here.
    """
    # Sync endpoint: the file is read here, and the provider call runs in FastAPI's thread pool
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    try:
        extracted = extract_text(file.filename, content)
    except QuestionParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    combined = extracted if not notes.strip() else f"{notes.strip()}\n\n{extracted}"
    combined = combined[:MAX_EXTRACTED_CHARS]
    return _run_generation(
        db, current_user,
        topic=topic.strip() or "the material provided below",
        count=count, difficulty=difficulty, language=language, notes=combined,
    )
