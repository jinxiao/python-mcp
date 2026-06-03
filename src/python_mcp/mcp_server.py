"""MCP server entry point for Codex."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from python_mcp.mcp_registry import register_mcp_tools


SERVER_INSTRUCTIONS = """
python-mcp exposes a searchable catalog for a public Python helper library.
Use it like API documentation for agents: search and inspect SDK methods, then
generate ordinary Python application code that imports python_mcp directly.

Use these tools when the user asks about:
- AWS STS or boto3 session helpers, including current STS session, current
  boto3 session settings, caller identity, assume-role, AWS account IDs, ARNs,
  and temporary credentials previews.
- SMTP email helpers, including building RFC 5322/MIME email messages,
  HTML email bodies, dry-run email sending, and SMTP send configuration.

Recommended workflow:
1. Search symbols with python_mcp_search_symbols using the user's domain terms.
2. Inspect the selected result with python_mcp_get_symbol_detail.
3. Generate code that imports the Python library directly.
4. Call a method through python_mcp_call_read_only_method only when read-only
   runtime confirmation is useful.

For prompts like "get the current STS session", prefer the indexed
python_mcp AwsStsClient helpers over generating raw boto3 calls from memory.
"""


def create_server() -> FastMCP:
    """Create and populate the MCP server."""

    mcp = FastMCP("python-mcp", instructions=SERVER_INSTRUCTIONS, json_response=True)
    register_mcp_tools(mcp)
    return mcp


mcp = create_server()


def main() -> None:
    """Run the MCP server over stdio."""

    mcp.run()


if __name__ == "__main__":
    main()
