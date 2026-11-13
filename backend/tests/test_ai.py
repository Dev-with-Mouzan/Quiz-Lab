"""Teacher AI settings and AI question drafting.

Provider HTTP calls are mocked, so no real API key or network access is needed.

    TEST_DATABASE_URL=sqlite:///./test_final.db  python -m tests.test_ai
"""
import json

import httpx

from tests.helpers import (
    TestClient, app, check, finish, admin_login, create_teacher, teacher_login,
    register_student, SessionLocal, auth,
)
from app.models import TeacherProfile, User
from app.services.ai_quiz import decrypt_api_key

REAL_POST = httpx.post
CALLS = []


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def install_fake(response):
    """Replace httpx.post. Every call is recorded in CALLS."""
    def fake_post(url, headers=None, json=None, timeout=None):
        CALLS.append({"url": url, "headers": headers or {}, "json": json})
        return response(url) if callable(response) else response
    httpx.post = fake_post


def restore():
    httpx.post = REAL_POST


def openai_reply(questions):
    return FakeResponse(200, {"choices": [{"message": {"content": json.dumps({"questions": questions})}}]})


def gemini_reply(questions):
    return FakeResponse(200, {"candidates": [{"content": {"parts": [
        {"text": "```json\n" + json.dumps({"questions": questions}) + "\n```"}]}}]})


GOOD = {"text": "What is 2+2?", "options": ["3", "4", "5", "6"], "correct_index": 1}
GOOD2 = {"text": "Capital of France?", "options": ["Paris", "Rome"], "correct_index": 0}
BAD = {"text": "Broken", "options": ["only one"], "correct_index": 5}

SECRET_KEY_VALUE = "sk-test-SECRETVALUE-ABCD1234"

with TestClient(app) as c:
    admin_h = admin_login(c)
    create_teacher(c, admin_h, "ai.teacher@gmail.com")
    th = teacher_login(c, "ai.teacher@gmail.com")
    student_h = register_student(c, "Ai", "Student", "ai.student@gmail.com", "34-AI-01", 2034)

    # ── Access control ──
    r = c.get("/api/ai/settings", headers=student_h)
    check("student cannot read AI settings", r.status_code == 403, str(r.status_code))

    # ── Fresh teacher: nothing configured ──
    r = c.get("/api/ai/settings", headers=th)
    body = r.json()
    check("settings start empty, 3 providers listed",
          r.status_code == 200 and body["has_key"] is False and body["provider"] is None
          and [p["id"] for p in body["providers"]] == ["openai", "deepseek", "gemini"], r.text[:200])

    r = c.post("/api/ai/generate-questions", headers=th, json={"topic": "Databases", "count": 2})
    check("generate without setup gives a clear message",
          r.status_code == 400 and "profile" in r.json()["detail"].lower(), r.text[:200])

    # ── Save OpenAI settings with the teacher's own key ──
    r = c.put("/api/ai/settings", headers=th, json={"provider": "openai", "model": "gpt-4o-mini",
                                                    "api_key": SECRET_KEY_VALUE})
    check("save OpenAI settings with key", r.status_code == 200 and r.json()["has_key"] is True, r.text[:200])

    r = c.get("/api/ai/settings", headers=th)
    check("settings show hint only, never the key",
          r.json()["key_hint"] == "1234" and SECRET_KEY_VALUE not in r.text, r.text[:200])

    db = SessionLocal()
    try:
        profile = db.query(TeacherProfile).join(User).filter(User.email == "ai.teacher@gmail.com").one()
        stored = profile.ai_api_key_enc
    finally:
        db.close()
    check("key is stored encrypted, not in plain text",
          stored and SECRET_KEY_VALUE not in stored and decrypt_api_key(stored) == SECRET_KEY_VALUE)

    # ── Generate: key goes to the provider in the Authorization header ──
    CALLS.clear()
    install_fake(openai_reply([GOOD, BAD, GOOD2]))
    r = c.post("/api/ai/generate-questions", headers=th,
               json={"topic": "Databases", "count": 2, "difficulty": "hard", "language": "English"})
    restore()
    body = r.json() if r.status_code == 200 else {}
    check("generate returns only valid drafts, up to count, in editor format",
          r.status_code == 200 and len(body.get("questions", [])) == 2
          and body["questions"][0] == {"text": "What is 2+2?", "options": ["3", "4", "5", "6"], "correct": 1},
          r.text[:300])
    check("invalid draft is dropped and counted", body.get("dropped") == 1, str(body.get("dropped")))
    check("OpenAI called with teacher's key and chosen model",
          CALLS and CALLS[0]["url"].startswith("https://api.openai.com")
          and CALLS[0]["headers"].get("Authorization") == f"Bearer {SECRET_KEY_VALUE}"
          and CALLS[0]["json"]["model"] == "gpt-4o-mini", str(CALLS[:1])[:200])

    # ── Provider errors become safe messages (no raw provider body) ──
    install_fake(FakeResponse(401, {"error": {"message": "Incorrect API key provided: sk-test-SECRETVALUE"}}))
    r = c.post("/api/ai/generate-questions", headers=th, json={"topic": "Databases", "count": 2})
    restore()
    check("rejected key gives a friendly message without echoing the key",
          r.status_code == 400 and "rejected this API key" in r.json()["detail"]
          and SECRET_KEY_VALUE not in r.text, r.text[:200])

    install_fake(FakeResponse(429, {"error": "quota"}))
    r = c.post("/api/ai/generate-questions", headers=th, json={"topic": "Databases", "count": 2})
    restore()
    check("quota error explained", r.status_code == 400 and "quota" in r.json()["detail"].lower(), r.text[:200])

    install_fake(FakeResponse(200, {"choices": [{"message": {"content": "not json at all"}}]}))
    r = c.post("/api/ai/generate-questions", headers=th, json={"topic": "Databases", "count": 2})
    restore()
    check("non-JSON reply handled", r.status_code == 400 and "JSON" in r.json()["detail"], r.text[:200])

    # ── Connection test ──
    install_fake(openai_reply([GOOD]))
    CALLS.clear()
    r = c.post("/api/ai/settings/test", headers=th, json={"provider": "openai", "model": "gpt-4o-mini"})
    restore()
    check("settings test uses the saved key for the saved provider",
          r.status_code == 200 and CALLS and CALLS[0]["headers"].get("Authorization") == f"Bearer {SECRET_KEY_VALUE}",
          r.text[:200])

    # A typed key is what gets tested, even if it is not saved
    install_fake(openai_reply([GOOD]))
    CALLS.clear()
    r = c.post("/api/ai/settings/test", headers=th,
               json={"provider": "openai", "model": "gpt-4o", "api_key": "sk-typed-KEY-5555"})
    restore()
    check("settings test uses the typed key and model on screen",
          r.status_code == 200 and CALLS[0]["headers"].get("Authorization") == "Bearer sk-typed-KEY-5555"
          and CALLS[0]["json"]["model"] == "gpt-4o", str(CALLS[:1])[:200])

    # Another provider with no key typed is refused (the saved key belongs to OpenAI)
    r = c.post("/api/ai/settings/test", headers=th, json={"provider": "deepseek", "model": "deepseek-chat"})
    check("testing an unsaved provider without a key is refused",
          r.status_code == 400 and "DeepSeek" in r.json()["detail"], r.text[:200])

    # Settings are not changed by a test
    r = c.get("/api/ai/settings", headers=th)
    check("a test does not change the saved provider",
          r.json()["provider"] == "openai" and r.json()["has_key"] is True, r.text[:200])

    # ── Switching provider needs a new key ──
    r = c.put("/api/ai/settings", headers=th, json={"provider": "gemini", "model": "gemini-2.5-flash"})
    check("switching provider without a new key is refused",
          r.status_code == 400 and "newly selected provider" in r.json()["detail"], r.text[:200])

    # ── Gemini with its own key, model in URL, key in header ──
    r = c.put("/api/ai/settings", headers=th, json={"provider": "gemini", "model": "gemini-2.5-flash",
                                                    "api_key": "AIza-GEMINI-KEY-9999"})
    check("save Gemini settings", r.status_code == 200, r.text[:200])
    CALLS.clear()
    install_fake(gemini_reply([GOOD2]))
    r = c.post("/api/ai/generate-questions", headers=th, json={"topic": "Networks", "count": 1})
    restore()
    check("Gemini: fenced JSON reply parsed, key in header not URL",
          r.status_code == 200 and len(r.json()["questions"]) == 1
          and "gemini-2.5-flash:generateContent" in CALLS[0]["url"]
          and "AIza-GEMINI-KEY-9999" not in CALLS[0]["url"]
          and CALLS[0]["headers"].get("x-goog-api-key") == "AIza-GEMINI-KEY-9999", r.text[:200])

    # ── Model name is validated before it reaches a URL ──
    r = c.put("/api/ai/settings", headers=th, json={"provider": "gemini", "model": "../evil/x",
                                                    "api_key": "AIza-GEMINI-KEY-9999"})
    check("model name with path characters rejected", r.status_code == 422, str(r.status_code))

    # ── Remove key ──
    r = c.delete("/api/ai/settings/key", headers=th)
    r2 = c.get("/api/ai/settings", headers=th)
    check("remove key clears it", r.status_code == 200 and r2.json()["has_key"] is False, r2.text[:200])

finish()
