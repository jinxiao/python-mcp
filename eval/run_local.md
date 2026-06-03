# Run Local MCP Effectiveness Eval

## Offline Runner

Run all cases:

```powershell
uv run python -m python_mcp.eval_runner
```

JSON output:

```powershell
uv run python -m python_mcp.eval_runner --format json
```

Single case:

```powershell
uv run python -m python_mcp.eval_runner --case aws_current_sts_session_zh
```

Default passing thresholds:

- Total score: at least 150/180
- Positive prompt Top-5 symbol hit rate: at least 90%
- Negative prompt forbidden symbol hits: 0
- Side-effect safety checks: all pass

## Codex Manual Test

1. Configure and restart Codex with the `python-mcp` MCP server.
2. Open `eval/codex_prompts.md`.
3. Send prompts to Codex one at a time.
4. Compare behavior with `eval/codex_expected.md`.

Codex should use MCP as a searchable API catalog, then generate direct Python
imports from `python_mcp`. MCP calls should not become production runtime code.
