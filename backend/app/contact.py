"""Sends contact-form submissions to the app owner's private inbox via
SMTP — the recipient address (CONTACT_EMAIL) is never exposed to the
frontend/client, only configured server-side. Works with any SMTP
provider; Gmail plus an App Password (myaccount.google.com/apppasswords)
is the simplest setup if you'd rather not sign up for a separate
email-sending service just for this."""

import re
import smtplib
from email.mime.text import MIMEText

from fastapi import HTTPException

from app.config import CONTACT_EMAIL, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USERNAME

MAX_MESSAGE_LENGTH = 5000
# Email headers are newline-delimited — a name/email containing a raw CR/LF
# could inject extra headers (e.g. forge additional recipients). A
# legitimate form field never needs a line break.
_HEADER_INJECTION_PATTERN = re.compile(r"[\r\n]")


def is_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD and CONTACT_EMAIL)


def send_contact_email(name: str, email: str, message: str) -> None:
    if not is_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "The contact form isn't set up yet. Set SMTP_HOST, SMTP_USERNAME, "
                "SMTP_PASSWORD, and CONTACT_EMAIL in the backend environment."
            ),
        )
    if _HEADER_INJECTION_PATTERN.search(name) or _HEADER_INJECTION_PATTERN.search(email):
        raise HTTPException(status_code=400, detail="Name and email can't contain line breaks.")
    if len(message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail=f"Message is too long (max {MAX_MESSAGE_LENGTH} characters).")

    msg = MIMEText(f"From: {name} <{email}>\n\n{message}")
    msg["Subject"] = f"ZeTruth Studio contact form: {name}"
    msg["From"] = SMTP_USERNAME
    msg["To"] = CONTACT_EMAIL
    msg["Reply-To"] = email

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
    except smtplib.SMTPException as exc:
        raise HTTPException(status_code=502, detail=f"Couldn't send the message: {exc}") from exc
