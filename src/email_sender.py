"""Gmail API helpers for sending the generated trading report by email."""

from __future__ import annotations

import base64
import os
from email.message import EmailMessage
from typing import List

import requests

from .logger import get_logger

logger = get_logger(__name__)

TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def _required_env(name: str) -> str:
    """Return a required environment variable or raise a clear error."""

    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def _split_recipients(raw_value: str) -> List[str]:
    """Split a comma-separated recipient list into clean addresses."""

    recipients = [item.strip() for item in raw_value.split(",")]
    recipients = [item for item in recipients if item]
    if not recipients:
        raise RuntimeError("EMAIL_TO must contain at least one recipient")
    return recipients


def _refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> str:
    """Exchange a refresh token for a short-lived Gmail access token."""

    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    access_token = str(payload.get("access_token", "")).strip()
    if not access_token:
        raise RuntimeError("Gmail token endpoint did not return an access token")
    return access_token


def _build_raw_message(sender: str, recipients: list[str], subject: str, body: str) -> str:
    """Build a Gmail-compatible base64url encoded MIME message."""

    message = EmailMessage()
    message["To"] = ", ".join(recipients)
    message["From"] = sender
    message["Subject"] = subject
    message.set_content(body, subtype="plain", charset="utf-8")
    raw_bytes = message.as_bytes()
    return base64.urlsafe_b64encode(raw_bytes).decode("utf-8").rstrip("=")


def send_report_email(subject: str, body: str) -> None:
    """Send the report via Gmail API using OAuth refresh-token credentials."""

    client_id = _required_env("GMAIL_CLIENT_ID")
    client_secret = _required_env("GMAIL_CLIENT_SECRET")
    refresh_token = _required_env("GMAIL_REFRESH_TOKEN")
    sender = _required_env("GMAIL_SENDER")
    recipients = _split_recipients(_required_env("EMAIL_TO"))

    try:
        access_token = _refresh_access_token(client_id, client_secret, refresh_token)
        raw_message = _build_raw_message(sender, recipients, subject, body)
        response = requests.post(
            GMAIL_SEND_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            json={"raw": raw_message},
            timeout=30,
        )
        response.raise_for_status()
        logger.info("Sent Gmail report email to %s", ", ".join(recipients))
    except Exception:
        raise
