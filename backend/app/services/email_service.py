import json
import smtplib
import urllib.request
from email.message import EmailMessage
from html import escape

from app.config import settings

# Brand colours (match the app's navy / amber theme)
NAVY = "#1F2A44"
AMBER = "#F59E0B"
TEXT = "#1F2937"
MUTED = "#64748B"
PAGE_BG = "#EEF2F7"


def _deliver(to_email: str, subject: str, text: str, html: str | None = None) -> None:
    """Send an email via Resend HTTP API, SMTP, or console (dev).

    `text` is always sent. `html` (optional) is the designed version; clients
    that cannot render HTML fall back to `text`.
    """
    if settings.EMAIL_PROVIDER == "resend" and settings.RESEND_API_KEY:
        message = {
            "from": settings.RESEND_FROM,
            "to": [to_email],
            "subject": subject,
            "text": text,
        }
        if html:
            message["html"] = html
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(message).encode(),
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
        msg.set_content(text)
        if html:
            msg.add_alternative(html, subtype="html")

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
    print(text)
    if html:
        print(" (HTML version also prepared; not shown in console)")
    print(line)


# ── HTML template ─────────────────────────────────────────────

def _render_layout(preheader: str, heading: str, content_html: str, footer_html: str) -> str:
    """Wrap content in the QuizLab email layout. Table-based and inline-styled
    so it renders the same in Gmail, Outlook and mobile clients."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(heading)}</title>
</head>
<body style="margin:0;padding:0;background:{PAGE_BG};font-family:'Segoe UI',Helvetica,Arial,sans-serif;color:{TEXT};">
  <span style="display:none;max-height:0;overflow:hidden;opacity:0;">{escape(preheader)}</span>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAGE_BG};padding:32px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#FFFFFF;border-radius:16px;overflow:hidden;">
          <tr>
            <td style="background:{NAVY};padding:28px 32px;">
              <div style="font-size:24px;font-weight:800;color:#FFFFFF;letter-spacing:-0.3px;">QuizLab</div>
              <div style="font-size:11px;color:#94A3B8;margin-top:6px;letter-spacing:1px;text-transform:uppercase;">CS Department &middot; Govt. Graduate College Burewala</div>
            </td>
          </tr>
          <tr>
            <td style="height:4px;background:{AMBER};font-size:0;line-height:0;">&nbsp;</td>
          </tr>
          <tr>
            <td style="padding:32px;">
              <h1 style="margin:0 0 14px;font-size:22px;line-height:1.3;color:{NAVY};">{escape(heading)}</h1>
              {content_html}
            </td>
          </tr>
          <tr>
            <td style="padding:20px 32px;background:#F8FAFC;border-top:1px solid #E2E8F0;font-size:12px;line-height:1.6;color:{MUTED};">
              {footer_html}
            </td>
          </tr>
        </table>
        <div style="font-size:11px;color:#94A3B8;margin-top:16px;">This is an automated message from QuizLab. Please do not reply to this email.</div>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _paragraph(text_html: str) -> str:
    return f'<p style="margin:0 0 14px;font-size:15px;line-height:1.6;color:{TEXT};">{text_html}</p>'


def _otp_block(code: str) -> str:
    """Highlighted code box, the main thing the reader needs to see."""
    return f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:22px 0;">
  <tr>
    <td align="center" style="background:#FFF8E7;border:1px dashed {AMBER};border-radius:12px;padding:22px 16px;">
      <div style="font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#92400E;">Your one-time code</div>
      <div style="font-size:36px;font-weight:800;letter-spacing:10px;color:{NAVY};font-family:Consolas,'Courier New',monospace;margin-top:10px;">{escape(code)}</div>
    </td>
  </tr>
</table>"""


def _button(label: str, url: str) -> str:
    return f"""
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:22px 0 8px;">
  <tr>
    <td style="background:{AMBER};border-radius:10px;">
      <a href="{escape(url)}" style="display:inline-block;padding:13px 26px;font-size:15px;font-weight:700;color:{NAVY};text-decoration:none;">{escape(label)}</a>
    </td>
  </tr>
</table>"""


def _steps(items: list[str]) -> str:
    rows = "".join(
        f'<tr><td valign="top" style="padding:0 12px 10px 0;"><div style="width:24px;height:24px;line-height:24px;text-align:center;border-radius:12px;background:{NAVY};color:#FFFFFF;font-size:12px;font-weight:700;">{i}</div></td>'
        f'<td valign="top" style="padding:2px 0 10px;font-size:14px;line-height:1.6;color:{TEXT};">{item}</td></tr>'
        for i, item in enumerate(items, 1)
    )
    return f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:6px 0 4px;">{rows}</table>'


# ── Public senders ────────────────────────────────────────────

def send_otp_email(to_email: str, otp_code: str, purpose: str = "registration") -> None:
    """Send a one-time code. purpose: 'registration' or 'password_reset'."""
    minutes = settings.OTP_EXPIRE_MINUTES
    if purpose == "password_reset":
        subject = "Your QuizLab password reset code"
        heading = "Reset your password"
        intro = "We received a request to reset the password for your QuizLab account. Use the code below to continue:"
        ignore = "If you did not ask to reset your password, you can ignore this email. Your password will not change."
    else:
        subject = "Your QuizLab verification code"
        heading = "Verify your email"
        intro = "Thanks for signing up for QuizLab. Enter the code below to verify your account:"
        ignore = "If you did not create a QuizLab account, you can safely ignore this email."

    text = (
        f"{heading}\n\n"
        f"Your QuizLab code is: {otp_code}\n\n"
        f"It expires in {minutes} minutes. {ignore}\n\n"
        "Regards,\nQuizLab — CS Department, Govt. Graduate College Burewala"
    )
    html = _render_layout(
        preheader=f"Your QuizLab code is {otp_code}. It expires in {minutes} minutes.",
        heading=heading,
        content_html=(
            _paragraph("Hello,")
            + _paragraph(escape(intro))
            + _otp_block(otp_code)
            + _paragraph(f"This code expires in <strong>{minutes} minutes</strong>. For your security, never share it with anyone.")
            + f'<p style="margin:18px 0 0;font-size:13px;line-height:1.6;color:{MUTED};">{escape(ignore)}</p>'
        ),
        footer_html="Regards,<br>QuizLab &mdash; CS Department, Govt. Graduate College Burewala",
    )
    _deliver(to_email, subject, text, html)


def send_credentials_email(to_email: str, name: str) -> None:
    """Tell a new teacher their account exists. No password is sent by email."""
    login_url = f"{settings.FRONTEND_URL.rstrip('/')}/login"
    subject = "Your QuizLab teacher account"
    text = (
        f"Hi {name},\n\n"
        "Your teacher account has been created for QuizLab "
        "(CS Department, Govt. Graduate College Burewala).\n\n"
        f"Account email: {to_email}\n\n"
        "For your security, your password is not sent by email. To set your password:\n"
        "1. Open the login page and choose \"Forgot password\".\n"
        "2. Enter this email address. We will send you a verification code.\n"
        "3. Enter the code and choose your new password.\n\n"
        f"Login page: {login_url}\n\n"
        "Regards,\nQuizLab — CS Department"
    )
    html = _render_layout(
        preheader="Your QuizLab teacher account is ready. Set your password to sign in.",
        heading=f"Welcome, {name}",
        content_html=(
            _paragraph(
                "Your teacher account has been created for <strong>QuizLab</strong>, "
                "the online quiz platform of the CS Department."
            )
            + f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:6px 0 4px;background:#F8FAFC;border-radius:10px;">
  <tr>
    <td style="padding:14px 18px;">
      <div style="font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:{MUTED};">Account email</div>
      <div style="font-size:15px;font-weight:600;color:{NAVY};margin-top:4px;">{escape(to_email)}</div>
    </td>
  </tr>
</table>"""
            + _paragraph("<strong>Set your password</strong> to sign in:")
            + _steps([
                'Open the login page and choose <strong>"Forgot password"</strong>.',
                "Enter the email address above. We will send you a verification code.",
                "Enter the code and choose your new password.",
            ])
            + _button("Go to login page", login_url)
            + f'<p style="margin:14px 0 0;font-size:13px;line-height:1.6;color:{MUTED};">For your security, your password is not included in this email.</p>'
        ),
        footer_html="Regards,<br>QuizLab &mdash; CS Department, Govt. Graduate College Burewala",
    )
    _deliver(to_email, subject, text, html)
