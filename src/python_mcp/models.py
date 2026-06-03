"""Shared public data models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AwsIdentity(BaseModel):
    """AWS caller identity returned by STS."""

    account: str = Field(description="AWS account ID.")
    arn: str = Field(description="AWS principal ARN.")
    user_id: str = Field(description="AWS user or role ID.")


class AwsCredentialsPreview(BaseModel):
    """STS credentials with sensitive values masked."""

    access_key_id: str
    secret_access_key: str
    session_token: str
    expiration: str | None = None


class EmailSendResult(BaseModel):
    """Result returned by email sending helpers."""

    dry_run: bool
    sender: str
    recipients: list[str]
    subject: str
    message_size: int
    metadata: dict[str, Any] = Field(default_factory=dict)
