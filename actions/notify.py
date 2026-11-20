"""Reminder delivery: email (SMTP) and text messages (Twilio). Both are optional.

* Email uses SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / SMTP_FROM / SMTP_STARTTLS.
  docker-compose points this at the bundled MailHog container by default, so reminder
  emails can be demoed at http://localhost:8025 without real credentials.
* Text messages use TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER. When those
  are missing, nothing is sent: Bloom says "Text reminders not configured" and logs the
  message it would have sent.
* Calendar reminders (.ics files with alarms) are created in the browser and always work.
"""

from __future__ import annotations

import base64
import json
import os
import smtplib
import urllib.parse
import urllib.request
from email.message import EmailMessage


def email_ready() -> bool:
    return bool(os.environ.get("SMTP_HOST", "").strip())


def sms_ready() -> bool:
    return all(os.environ.get(k, "").strip() for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER"))


def send_email(to: str, subject: str, text: str) -> tuple[bool, str]:
    if not email_ready():
        print(f"notify: email reminders not configured; would have emailed {to}: {subject}", flush=True)
        return False, "Email reminders not configured"
    message = EmailMessage()
    message["From"] = os.environ.get("SMTP_FROM", "Bloom <reminders@bloom.local>")
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    try:
        port = int(os.environ.get("SMTP_PORT", "25") or 25)
        with smtplib.SMTP(os.environ["SMTP_HOST"], port, timeout=15) as smtp:
            if os.environ.get("SMTP_STARTTLS", "").lower() in ("1", "true", "yes"):
                smtp.starttls()
            if os.environ.get("SMTP_USER"):
                smtp.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
            smtp.send_message(message)
        return True, "sent"
    except (OSError, smtplib.SMTPException) as error:
        print(f"notify: email to {to} failed: {error}", flush=True)
        return False, f"Email could not be sent: {error.__class__.__name__}"


def normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit() or ch == "+")
    if digits and not digits.startswith("+"):
        digits = "+1" + digits[-10:] if len(digits) >= 10 else digits
    return digits


def send_sms(to: str, text: str) -> tuple[bool, str]:
    to = normalize_phone(to)
    if not sms_ready():
        print(f"notify: Text reminders not configured; would have texted {to}: {text}", flush=True)
        return False, "Text reminders not configured"
    sid = os.environ["TWILIO_ACCOUNT_SID"]
    data = urllib.parse.urlencode({"To": to, "From": os.environ["TWILIO_FROM_NUMBER"], "Body": text[:600]}).encode()
    request = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", data=data)
    token = base64.b64encode(f"{sid}:{os.environ['TWILIO_AUTH_TOKEN']}".encode()).decode()
    request.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.loads(response.read() or b"{}")
        return True, body.get("sid", "sent")
    except Exception as error:  # network errors, bad numbers, auth problems
        print(f"notify: text to {to} failed: {error}", flush=True)
        return False, f"Text could not be sent: {error.__class__.__name__}"


def reminder_text(event: dict, timing: str, lang: str = "en") -> tuple[str, str]:
    """Subject and body for a reminder, in English or Spanish."""
    from actions.i18n import friendly_date_in

    when = friendly_date_in(event["date"], lang)
    link = event.get("source_url") or event.get("url") or ""
    if lang == "es":
        soon = {"1d": "mañana", "2h": "en 2 horas", "3d": "en 3 días", "1w": "en una semana", "2w": "en dos semanas"}.get(timing, "pronto")
        subject = f"Recordatorio de Bloom: {event['title']} es {soon}"
        body = (f"¡Hola! 🌸\n\nLe recordamos que {event['title']} es {soon}.\n\n"
                f"Cuándo: {when}, {event['time']}\nDónde: {event['location']}\n" + (f"Más información: {link}\n" if link else "") +
                "\nPor favor confirme los detalles con los organizadores.\n\nCon cariño,\nBloom · Salem, Oregon")
    else:
        soon = {"1d": "tomorrow", "2h": "in 2 hours", "3d": "in 3 days", "1w": "in one week", "2w": "in two weeks"}.get(timing, "coming up")
        subject = f"Bloom reminder: {event['title']} is {soon}"
        body = (f"Hello! 🌸\n\nJust a friendly reminder that {event['title']} is {soon}.\n\n"
                f"When: {when}, {event['time']}\nWhere: {event['location']}\n" + (f"More info: {link}\n" if link else "") +
                "\nPlease check details with the host before you go.\n\nWarmly,\nBloom · Salem, Oregon")
    return subject, body
