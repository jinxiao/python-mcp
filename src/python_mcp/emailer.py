"""Email helper classes.

The default send path is dry-run so the helper is safe to expose in demos.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.parser import Parser
from email.policy import default

from python_mcp.config import SmtpConfig
from python_mcp.models import EmailSendResult


class EmailClient:
    """Importable SMTP email SDK helper for messages, previews, and sending.

    Use this class directly from Python application code to build RFC 5322/MIME
    messages, include HTML email bodies, create dry-run send_email previews, or
    send through SMTP. The MCP adapter indexes this class so agents can discover
    the API and generate direct imports.
    """

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool | None = None,
        default_sender: str | None = None,
    ) -> None:
        config = SmtpConfig.from_env()
        self.smtp_host = smtp_host or config.host
        self.smtp_port = smtp_port or config.port
        self.username = username or config.username
        self.password = password or config.password
        self.use_tls = config.use_tls if use_tls is None else use_tls
        self.default_sender = default_sender or config.default_sender

    def build_message(
        self,
        sender: str,
        recipients: list[str],
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> str:
        """Build an RFC 5322/MIME email message with optional HTML and return text."""

        message = EmailMessage()
        message["From"] = sender
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        message.set_content(body)
        if html_body:
            message.add_alternative(html_body, subtype="html")
        return message.as_string()

    def send_email(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        sender: str | None = None,
        html_body: str | None = None,
        dry_run: bool = True,
    ) -> EmailSendResult:
        """Send an SMTP email or create a dry-run preview result.

        When `dry_run` is true, no SMTP connection is opened.
        """

        resolved_sender = sender or self.default_sender
        if not resolved_sender:
            raise ValueError("sender is required when no default sender is configured")

        message_text = self.build_message(
            sender=resolved_sender,
            recipients=recipients,
            subject=subject,
            body=body,
            html_body=html_body,
        )

        if dry_run:
            return EmailSendResult(
                dry_run=True,
                sender=resolved_sender,
                recipients=recipients,
                subject=subject,
                message_size=len(message_text),
                metadata={"smtp_host": self.smtp_host, "sent": False},
            )

        if not self.smtp_host:
            raise ValueError("smtp_host is required when dry_run is false")

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
            if self.use_tls:
                smtp.starttls()
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.send_message(Parser(policy=default).parsestr(message_text))

        return EmailSendResult(
            dry_run=False,
            sender=resolved_sender,
            recipients=recipients,
            subject=subject,
            message_size=len(message_text),
            metadata={"smtp_host": self.smtp_host, "sent": True},
        )
