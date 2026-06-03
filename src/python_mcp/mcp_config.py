"""Configuration for the non-invasive MCP adapter."""

from __future__ import annotations

import os


def _csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(name)
    if raw is None:
        return default
    return tuple(part.strip() for part in raw.split(",") if part.strip())


MCP_SCAN_PACKAGES = _csv_env("PYTHON_MCP_SCAN_PACKAGES", ("python_mcp",))

MCP_EXCLUDE_MODULE_PREFIXES = _csv_env(
    "PYTHON_MCP_EXCLUDE_MODULE_PREFIXES",
    (
        "python_mcp.mcp_",
        "python_mcp.models",
        "python_mcp.config",
    ),
)

MCP_REGISTER_METHOD_TOOLS = (
    os.getenv("PYTHON_MCP_REGISTER_METHOD_TOOLS", "").strip().lower()
    in {"1", "true", "yes", "on"}
)
