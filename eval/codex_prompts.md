# Codex MCP Effectiveness Prompts

Use these prompts directly in Codex after the `python-mcp` server is configured.
Expected behavior is listed in `eval/codex_expected.md`.

## AWS STS / boto3 Session

1. 获取当前 AWS STS session 设置，包含当前 profile 和 region。
2. Which helper should I use for current boto3 session settings?
3. 我想查看当前 boto3 profile 和 region，不要暴露 AWS credentials。
4. Generate Python code to get AWS caller identity, account ID, and ARN.
5. 查询当前 AWS account ID 和 principal ARN，应该用哪个 helper？
6. 我想 assume role 并预览 temporary credentials，不要直接暴露 secret。
7. Find the helper for an assume-role temporary credentials preview.
8. How do I inspect the active STS helper session without raw boto3 calls?

## SMTP Email

1. 构建 RFC 5322/MIME 邮件文本，收件人、主题和正文都要支持。
2. 我需要生成带 HTML body 的 SMTP email message。
3. Generate Python code to send a safe dry-run SMTP email preview.
4. SMTP email 发送前，我想看 dry-run preview 和配置字段。
5. Which SDK method builds an RFC 5322 MIME message with optional HTML?
6. Find the send_email helper for an SMTP dry run.

## Negative Samples

1. 用 Python 读取 CSV 并统计行数。
2. 写一个 FastAPI health check endpoint。
3. Parse a JSON file in Python and print each record.
4. Write a unit test for a calculator add function.
