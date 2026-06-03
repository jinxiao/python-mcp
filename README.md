# python-mcp

`python-mcp` is a small public Python library plus a non-invasive MCP adapter.

The package includes normal reusable classes, such as AWS STS helpers and email
helpers. The MCP server lives beside the library and uses Griffe at startup to
inspect public classes and methods, then exposes an indexed catalog to Codex.

## Install from GitHub Release

Download and install the wheel from a GitHub Release:

```powershell
uv tool install https://github.com/jinxiao/python-mcp/releases/download/v0.1.0/python_mcp-0.1.0-py3-none-any.whl
```

After installation, the MCP server command is available as:

```powershell
python_mcp
```

To upgrade to a newer release, install the newer wheel with `--force`:

```powershell
uv tool install --force https://github.com/jinxiao/python-mcp/releases/download/v0.1.1/python_mcp-0.1.1-py3-none-any.whl
```

To uninstall:

```powershell
uv tool uninstall python-mcp
```

GitHub Release is not a Python package index, so bare `uvx python_mcp` is not
the right install model for release assets. Use `uv tool install` once, then
configure MCP clients to run the installed `python_mcp` command.

## Run locally during development

From this repository root:

```powershell
uv run python -m python_mcp.mcp_server
```

This repository is an installable Python package with a `src` layout. For local
development, the important part is that the MCP client starts the command from
this repository root, either by setting `cwd` or by passing `--directory` to
`uv`. If the client cannot find `uv` from its `PATH`, replace `"uv"` with the
absolute path to `uv.exe`.

Codex MCP configuration for local development:

```json
{
  "command": "uv",
  "args": ["run", "python", "-m", "python_mcp.mcp_server"],
  "cwd": "C:\\Users\\admin\\python-mcp"
}
```

## Configure GitHub Copilot in VS Code

VS Code stores MCP servers in an `mcp.json` file. After installing the tool,
create `.vscode/mcp.json` in your workspace or open the user-level file with
`MCP: Open User Configuration`:

```json
{
  "servers": {
    "pythonMcp": {
      "type": "stdio",
      "command": "python_mcp"
    }
  }
}
```

After saving the file, use `MCP: List Servers` to start, stop, restart, or
inspect the server.

## Configure OpenCode

OpenCode stores MCP servers under the `mcp` key in `opencode.json` or
`opencode.jsonc`. After installing the tool, add this server to the config file
you use for OpenCode:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "pythonMcp": {
      "type": "local",
      "command": ["python_mcp"],
      "enabled": true
    }
  }
}
```

After changing the config, restart the MCP server or the client session so the
tool catalog is rebuilt.

## Publish a GitHub Release

The release workflow builds and uploads package artifacts when you push a
version tag:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

The workflow runs tests, builds `dist/*.whl` and `dist/*.tar.gz`, then attaches
them to the GitHub Release for the tag.

## Configure scanning

By default the adapter scans the `python_mcp` package and skips the internal
MCP adapter modules.

Environment variables:

- `PYTHON_MCP_SCAN_PACKAGES`: comma-separated package names to scan.
- `PYTHON_MCP_EXCLUDE_MODULE_PREFIXES`: comma-separated module prefixes to skip.
- `PYTHON_MCP_REGISTER_METHOD_TOOLS`: set to `true` to also expose one MCP tool
  per public method. The default indexed mode is recommended for larger
  libraries.

## Indexed MCP tools

The default MCP server exposes a small fixed toolset:

- `python_mcp_list_modules`
- `python_mcp_search_symbols`
- `python_mcp_get_symbol_detail`
- `python_mcp_call_read_only_method`
- `python_mcp_call_method`

## Use from other applications

Treat this package as a normal Python SDK. MCP is the searchable API catalog
that helps agents find the right SDK method, inspect its signature, and generate
ordinary application code.

Application code should import the library directly:

```python
from python_mcp.emailer import EmailClient

client = EmailClient(default_sender="from@example.com")
preview = client.send_email(
    recipients=["to@example.com"],
    subject="Hello",
    body="Plain body",
)
```

Recommended agent workflow for app development:

1. Search the MCP catalog with `python_mcp_search_symbols`.
2. Inspect the selected symbol with `python_mcp_get_symbol_detail`.
3. Generate code that imports `python_mcp` modules directly.
4. Use `python_mcp_call_read_only_method` only for optional read-only runtime
   checks.

For AWS STS requests such as "current STS session", "current boto3 session",
"caller identity", "AWS account ID", or "assume role", search this MCP catalog
first instead of writing raw `boto3` calls from memory.

Avoid making MCP the production runtime dependency for ordinary Python apps.
MCP calls are best kept for discovery, documentation lookup, and safe
verification while writing or testing code.

### Helping Codex discover the MCP automatically

Codex decides whether to run `tool_search` from the installed MCP metadata. A
server cannot force that decision, so the best way to make discovery work from
natural prompts is to put concrete use cases and domain terms in the server
instructions and tool descriptions.

This MCP advertises AWS STS/boto3 session helpers and SMTP email helpers in its
metadata. After changing those descriptions, restart the MCP/Codex session so
the deferred tool index is rebuilt.

Recommended Codex flow:

1. Search for relevant symbols.
2. Inspect the selected symbol detail.
3. Generate code that imports the Python library directly.
4. Call a method through MCP only when runtime confirmation is useful.

Example prompt:

```text
Use python_mcp_search_symbols to find the current STS session helper, inspect
the symbol detail, then write Python code that imports AwsStsClient directly.
```

Read-only catalog tools are registered with MCP `readOnlyHint=true` annotations
so clients can run discovery and lookup operations without side-effect
confirmation. Use `python_mcp_call_read_only_method` for read-only runtime
checks. `python_mcp_call_method` remains available for methods with unknown
safety, which require `allow_side_effects=true`.

## Configure AWS and SMTP

AWS uses the standard boto3 credential chain. SMTP configuration is read from
environment variables only when an `EmailClient` instance is created by the MCP
factory.

- `AWS_PROFILE`
- `AWS_REGION`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_USE_TLS`
- `SMTP_DEFAULT_SENDER`
