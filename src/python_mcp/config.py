"""Environment-backed configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AwsConfig:
    """Configuration for boto3-backed helpers."""

    profile_name: str | None = None
    region_name: str | None = None

    @classmethod
    def from_env(cls) -> "AwsConfig":
        """Load AWS config from environment variables."""

        return cls(
            profile_name=os.getenv("AWS_PROFILE"),
            region_name=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"),
        )


@dataclass(frozen=True)
class SmtpConfig:
    """Configuration for SMTP-backed helpers."""

    host: str | None = None
    port: int = 587
    username: str | None = None
    password: str | None = None
    use_tls: bool = True
    default_sender: str | None = None

    @classmethod
    def from_env(cls) -> "SmtpConfig":
        """Load SMTP config from environment variables."""

        return cls(
            host=os.getenv("SMTP_HOST"),
            port=int(os.getenv("SMTP_PORT", "587")),
            username=os.getenv("SMTP_USERNAME"),
            password=os.getenv("SMTP_PASSWORD"),
            use_tls=_bool_env("SMTP_USE_TLS", True),
            default_sender=os.getenv("SMTP_DEFAULT_SENDER"),
        )
