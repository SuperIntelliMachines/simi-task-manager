from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid

from app.core.config import get_settings


class EmailDeliveryError(RuntimeError):
    pass


class EmailService:
    def __init__(
        self,
        *,
        smtp_host: str = "",
        smtp_port: int = 587,
        smtp_username: str = "",
        smtp_password: str = "",
        from_email: str = "",
    ):
        self.smtp_host = smtp_host.strip()
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username.strip()
        self.smtp_password = smtp_password
        self.from_email = from_email.strip()

    @classmethod
    def from_settings(cls) -> EmailService:
        settings = get_settings()
        return cls(
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            smtp_username=settings.smtp_username,
            smtp_password=settings.smtp_password,
            from_email=settings.from_email,
        )

    def is_configured(self) -> bool:
        return bool(
            self.smtp_host
            and self.smtp_username
            and self.smtp_password
            and self.from_email
        )

    async def send_email(
        self,
        *,
        to: str,
        subject: str,
        text: str,
        html: str | None = None,
    ) -> str:
        if not self.is_configured():
            raise EmailDeliveryError("SMTP email is not configured")

        recipient = to.strip()
        if not recipient:
            raise EmailDeliveryError("email recipient is required")

        return await asyncio.to_thread(
            self._send_smtp_email,
            recipient=recipient,
            subject=subject,
            text=text,
            html=html,
        )

    def _send_smtp_email(
        self,
        *,
        recipient: str,
        subject: str,
        text: str,
        html: str | None,
    ) -> str:
        message = EmailMessage()
        message["From"] = self.from_email
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(text)
        if html:
            message.add_alternative(html, subtype="html")

        message_id = make_msgid(domain=self.smtp_host or None)
        message["Message-ID"] = message_id

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                refused = server.send_message(message)
        except smtplib.SMTPException as exc:
            raise EmailDeliveryError(str(exc)) from exc

        if refused:
            raise EmailDeliveryError(f"SMTP refused recipients: {refused}")

        return message_id.strip("<>")
