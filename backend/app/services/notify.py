"""Deliver one-time codes. Never log the code or the raw destination."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from urllib.parse import urlparse

import httpx

from app.observability.logging import get_logger
from app.services.formatter import hash_identifier
from app.settings import get_settings

log = get_logger("termpilot.notify")

# Populated only when TERMPILOT_ENV=test so pytest can complete the flow.
LAST_OTP: dict[str, str] = {}
LAST_MAIL_STATUS = "unset"
RESEND_DEV_FROM = "TermPilot <beth.t@example.com>"


def _purpose_copy(purpose: str) -> str:
    if purpose == "signup":
        return "Confirm your TermPilot campus account"
    if purpose == "phone":
        return "Confirm your phone for TermPilot 2FA"
    return "Your TermPilot sign-in code"


async def deliver_otp(dest: str, channel: str, code: str, purpose: str) -> None:
    settings = get_settings()
    dest_hash = hash_identifier(dest)
    if settings.env == "test" or os.environ.get("PYTEST_CURRENT_TEST"):
        LAST_OTP[f"{channel}:{dest}"] = code
        log.info("otp_issued", channel=channel, dest=dest_hash, purpose=purpose)
        if settings.env == "test":
            return
    subject = _purpose_copy(purpose)
    body = (
        f"{subject}.\n\n"
        f"Your TermPilot code is {code}. It expires in 10 minutes.\n\n"
        "If you did not request this, ignore the message. Never forward this code.\n"
        "Support: support@termpilot.org\n"
    )
    html = (
        f"<p>{subject}.</p>"
        f"<p style='font-size:28px;letter-spacing:0.2em;font-family:monospace'><strong>{code}</strong></p>"
        "<p>This code expires in 10 minutes. If you did not request it, ignore this email.</p>"
        "<p>TermPilot · <a href='mailto:support@termpilot.org'>support@termpilot.org</a></p>"
    )
    try:
        if channel == "sms":
            await _send_sms(dest, f"TermPilot code {code}. Expires in 10 minutes.")
        else:
            await _send_email(dest, subject, body, html)
    except Exception as exc:  # noqa: BLE001
        log.warning("otp_delivery_failed", channel=channel, dest=dest_hash, error=type(exc).__name__)
    else:
        log.info("otp_issued", channel=channel, dest=dest_hash, purpose=purpose)


async def _send_resend(to_addr: str, subject: str, body: str, html: str | None, from_addr: str) -> httpx.Response:
    settings = get_settings()
    payload: dict[str, object] = {
        "from": from_addr,
        "to": [to_addr],
        "reply_to": settings.reply_to_email,
        "subject": subject,
        "text": body,
    }
    if html:
        payload["html"] = html
    async with httpx.AsyncClient(timeout=10) as client:
        return await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json=payload,
        )


async def _send_email(to_addr: str, subject: str, body: str, html: str | None = None) -> None:
    global LAST_MAIL_STATUS
    settings = get_settings()
    if settings.resend_api_key:
        response = await _send_resend(to_addr, subject, body, html, settings.auth_from_email)
        if response.status_code >= 400:
            log.warning(
                "otp_resend_rejected",
                status=response.status_code,
                body=response.text[:240],
            )
            fallback = await _send_resend(to_addr, subject, body, html, RESEND_DEV_FROM)
            if fallback.status_code >= 400:
                LAST_MAIL_STATUS = f"resend_{fallback.status_code}"
                fallback.raise_for_status()
            LAST_MAIL_STATUS = "resend_dev"
            return
        LAST_MAIL_STATUS = "resend"
        return
    smtp_url = settings.smtp_url
    if smtp_url:
        parsed = urlparse(smtp_url)
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.auth_from_email
        msg["To"] = to_addr
        msg.set_content(body)
        host = parsed.hostname or "localhost"
        port = parsed.port or 587
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.starttls()
            if parsed.username:
                smtp.login(parsed.username, parsed.password or "")
            smtp.send_message(msg)
        return
    LAST_MAIL_STATUS = "no_key"
    log.warning("otp_skipped_no_provider", channel="email")


async def _send_sms(to_number: str, body: str) -> None:
    settings = get_settings()
    if not (settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from):
        if settings.env != "production":
            log.info("otp_skipped_no_provider", channel="sms")
        return
    url = (
        "https://api.twilio.com/2010-04-01/Accounts/"
        f"{settings.twilio_account_sid}/Messages.json"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            url,
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            data={"From": settings.twilio_from, "To": to_number, "Body": body},
        )
        response.raise_for_status()
