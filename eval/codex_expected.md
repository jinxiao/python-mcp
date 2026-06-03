# Codex MCP Effectiveness Expected Behavior

## Positive AWS Prompts

Codex should discover and use the `python_mcp` MCP catalog before writing code.
Expected tool flow:

1. `python_mcp_search_symbols`
2. `python_mcp_get_symbol_detail`
3. Optional `python_mcp_call_read_only_method` only for read-only checks

Expected symbols:

- Current STS/session/profile/region prompts: `python_mcp.aws_sts:AwsStsClient.get_current_sts_session` or `python_mcp.aws_sts:AwsStsClient.describe_session`
- Caller identity/account/ARN prompts: `python_mcp.aws_sts:AwsStsClient.get_caller_identity`
- Assume-role/temporary credentials prompts: `python_mcp.aws_sts:AwsStsClient.assume_role`

Final code should use direct SDK imports, for example:

```python
from python_mcp.aws_sts import AwsStsClient
```

Assume-role is not read-only. Codex should not call it through
`python_mcp_call_read_only_method`; it should explain that side-effect
permission is required for runtime confirmation.

## Positive SMTP Prompts

Codex should discover and use the `python_mcp` MCP catalog before writing code.
Expected symbols:

- MIME/RFC 5322/HTML message prompts: `python_mcp.emailer:EmailClient.build_message`
- SMTP dry-run/send preview prompts: `python_mcp.emailer:EmailClient.send_email`

Final code should use direct SDK imports, for example:

```python
from python_mcp.emailer import EmailClient
```

For dry-run prompts, generated code should keep `dry_run=True` unless the prompt
explicitly asks to send a real email.

## Negative Prompts

Codex should not use `python_mcp` for unrelated CSV, JSON, FastAPI, or calculator
unit-test tasks. It should answer using ordinary Python/library knowledge.

## Manual Score

Score each prompt out of 10:

- 2: correct route, using `python_mcp` only for AWS STS or SMTP email tasks
- 3: expected symbol selected
- 2: symbol detail inspected before code generation
- 2: read-only and side-effect safety handled correctly
- 1: final code imports `python_mcp` SDK directly instead of treating MCP as runtime code
