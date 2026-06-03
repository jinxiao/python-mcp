"""Factories used by the MCP adapter to instantiate existing classes."""

from __future__ import annotations

from typing import Any

from python_mcp.aws_sts import AwsStsClient
from python_mcp.emailer import EmailClient


def create_aws_sts_client() -> AwsStsClient:
    """Create the default AWS STS helper for MCP calls."""

    return AwsStsClient()


def create_email_client() -> EmailClient:
    """Create the default email helper for MCP calls."""

    return EmailClient()


MCP_CLASS_FACTORIES: dict[str, Any] = {
    "python_mcp.aws_sts.AwsStsClient": create_aws_sts_client,
    "python_mcp.emailer.EmailClient": create_email_client,
}
