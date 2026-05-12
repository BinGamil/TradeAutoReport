"""Gmail delivery helpers for generated trading reports."""

from __future__ import annotations

import base64
from email.message import EmailMessage
import os
from pathlib import Path
from typing import Iterable

import requests

from .logger import get_logger

logger = get_logger(__name__)

TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def _google_error_message(response: requests.Response, fallback: str) -> str:
    """Return a safe, readable Google API error without exposing credentials."""

    try:
        payload = response.json()
    except ValueError:
        return fallback

    error = payload.get("error")
    description = payload.get("error_description")
    if isinstance(error, dict):
        message = error.get("message")
        status = error.get("status")
        details = " ".join(str(item) for item in (status, message) if item)
        return details or fallback

    details = " ".join(str(item) for item in (error, description) if item)
    return details or fallback


def _split_recipients(value: str) -> list[str]:
    return [item.strip() for item in value.replace(";", ",").split(",") if item.strip()]


def _required_env() -> dict[str, str] | None:
    names = [
        "GMAIL_CLIENT_ID",
        "GMAIL_CLIENT_SECRET",
        "GMAIL_REFRESH_TOKEN",
        "GMAIL_SENDER",
        "EMAIL_TO",
    ]
    values = {name: os.getenv(name, "").strip() for name in names}
    missing = [name for name, value in values.items() if not value]
    if missing:
        logger.info("Skipping email delivery; missing environment variables: %s", ", ".join(missing))
        return None
    return values


def _get_access_token(env_values: dict[str, str]) -> str:
    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": env_values["GMAIL_CLIENT_ID"],
            "client_secret": env_values["GMAIL_CLIENT_SECRET"],
            "refresh_token": env_values["GMAIL_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    if not response.ok:
        details = _google_error_message(response, response.reason)
        raise RuntimeError(f"Gmail OAuth token refresh failed: {details}")

    payload = response.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise RuntimeError("Gmail token response did not include an access token.")
    return str(access_token)


def _build_message(
    *,
    sender: str,
    recipients: Iterable[str],
    subject: str,
    body: str,
    attachment_path: str | Path | None,
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)

    message.add_alternative(
        "<p>"
        + body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        + "</p>",
        subtype="html",
    )

    if attachment_path:
        path = Path(attachment_path)
        if path.exists():
            message.add_attachment(
                path.read_bytes(),
                maintype="text",
                subtype="html",
                filename=path.name,
            )
        else:
            logger.warning("HTML attachment does not exist: %s", path)

    return message


def send_report_email(subject: str, body: str, attachment_path: str | Path | None = None) -> None:
    """Send a trading report email with the latest HTML report attached.

    Missing Gmail settings cause a clean skip. Network or Gmail errors are
    raised so callers can log them while keeping report generation successful.
    """

    env_values = _required_env()
    if not env_values:
        return

    recipients = _split_recipients(env_values["EMAIL_TO"])
    if not recipients:
        logger.info("Skipping email delivery; EMAIL_TO has no usable recipients.")
        return

    access_token = _get_access_token(env_values)
    message = _build_message(
        sender=env_values["GMAIL_SENDER"],
        recipients=recipients,
        subject=subject,
        body=body,
        attachment_path=attachment_path,
    )
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    response = requests.post(
        GMAIL_SEND_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        json={"raw": raw_message},
        timeout=30,
    )
    if not response.ok:
        details = _google_error_message(response, response.reason)
        raise RuntimeError(f"Gmail send failed: {details}")

    logger.info("Report email sent to %s.", ", ".join(recipients))
