import json
import smtplib
import urllib.request
from email.message import EmailMessage

from app.config import settings


def _deliver(to_email: str, subject: str, body: str) -> None:
    """Send a plain-text email via Resend HTTP API, SMTP, or console (dev)."""
    if settings.EMAIL_PROVIDER == "resend" and settings.RESEND_API_KEY:
        payload = json.dumps({
            "from": settings.RESEND_FROM,
            "to": [to_email],
            "subject": subject,
            "text": body,
        }).encode()
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as exc:  # noqa: BLE001 — report, never crash auth flow
            detail = ""
            if hasattr(exc, "read"):
                try:
                    detail = exc.read().decode(errors="replace")[:300]
                except Exception:
                    pass
            print(f"[EMAIL] Resend delivery failed for {to_email}: {exc} {detail}")
        return

    elif settings.EMAIL_PROVIDER == "smtp":
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = to_email
        msg.set_content(body)

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_TLS:
                    server.starttls()
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
        except Exception as exc:  # noqa: BLE001 — report, never crash auth flow
            print(f"[EMAIL] SMTP delivery failed for {to_email}: {exc}")
        return

    # Console/test provider — print to the server terminal in development.
    line = "=" * 58
    print(line)
    print(" TEST MODE - EMAIL DISABLED (set RESEND_API_KEY to send)")
    print(f" To:      {to_email}")
    print(f" Subject: {subject}")
    print(" Body:")
    print(body)
    print(line)


def send_otp_email(to_email: str, otp_code: str) -> None:
    """Send a one-time verification code via email."""
    body = (
        f"Your QuizLab verification code is: {otp_code}\n\n"
        "It expires in 10 minutes. If you did not request this code, "
        "you can safely ignore this email.\n\n"
        "Regards,\nQuizLab — CS Department, Govt. Graduate College Burewala"
    )
    _deliver(to_email, "Your QuizLab verification code", body)


def send_credentials_email(to_email: str, name: str, password: str) -> None:
    """Send teacher credentials via email."""
    body = (
        f"Hi {name},\n\n"
        "Your teacher account has been created for QuizLab "
        "(CS Department, Govt. Graduate College Burewala).\n\n"
        f"Email:    {to_email}\n"
        f"Password: {password}\n\n"
        "You can sign in at the login page using these credentials.\n\n"
        "Regards,\nQuizLab — CS Department"
    )
    _deliver(to_email, "Your QuizLab teacher account", body)
