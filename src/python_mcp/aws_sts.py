"""AWS STS helper classes.

These classes are ordinary public-library code. They do not import MCP or use
MCP decorators; the MCP adapter discovers them from the outside.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import boto3

from python_mcp.config import AwsConfig
from python_mcp.models import AwsCredentialsPreview, AwsIdentity


def _mask_secret(value: str | None, visible: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible:
        return "*" * len(value)
    return f"{value[:visible]}{'*' * max(len(value) - visible, 4)}"


class AwsStsClient:
    """Importable AWS STS SDK helper using boto3's default credential chain.

    Use this class directly from Python application code when you need the
    current STS session, current boto3 session settings, caller identity, AWS
    account ID, principal ARN, assume-role sessions, or temporary credentials
    previews. The MCP adapter only indexes this class so agents can discover
    the API and generate direct imports.
    """

    def __init__(
        self,
        profile_name: str | None = None,
        region_name: str | None = None,
    ) -> None:
        config = AwsConfig.from_env()
        self.profile_name = profile_name or config.profile_name
        self.region_name = region_name or config.region_name
        self._session = boto3.Session(
            profile_name=self.profile_name,
            region_name=self.region_name,
        )

    def get_caller_identity(self) -> AwsIdentity:
        """Return the AWS account ID, principal ARN, and user ID for active credentials."""

        response = self._session.client("sts").get_caller_identity()
        return AwsIdentity(
            account=response["Account"],
            arn=response["Arn"],
            user_id=response["UserId"],
        )

    def assume_role(
        self,
        role_arn: str,
        session_name: str,
        duration_seconds: int = 3600,
        external_id: str | None = None,
    ) -> AwsCredentialsPreview:
        """Assume an AWS IAM role and return a masked temporary credentials preview."""

        kwargs: dict[str, Any] = {
            "RoleArn": role_arn,
            "RoleSessionName": session_name,
            "DurationSeconds": duration_seconds,
        }
        if external_id:
            kwargs["ExternalId"] = external_id

        response = self._session.client("sts").assume_role(**kwargs)
        credentials = response["Credentials"]
        expiration = credentials.get("Expiration")
        if isinstance(expiration, datetime):
            expiration_text = expiration.isoformat()
        else:
            expiration_text = str(expiration) if expiration else None

        return AwsCredentialsPreview(
            access_key_id=_mask_secret(credentials.get("AccessKeyId")),
            secret_access_key=_mask_secret(credentials.get("SecretAccessKey")),
            session_token=_mask_secret(credentials.get("SessionToken")),
            expiration=expiration_text,
        )

    def describe_session(self) -> dict[str, str | None]:
        """Return current STS/boto3 session settings without exposing AWS credentials."""

        return {
            "profile_name": self.profile_name,
            "region_name": self.region_name,
        }

    def get_current_sts_session(self) -> dict[str, str | None]:
        """Return current STS session settings for the active python_mcp AWS helper."""

        return self.describe_session()
