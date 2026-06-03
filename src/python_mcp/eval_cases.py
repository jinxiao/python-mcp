"""Effectiveness benchmark cases for the python-mcp catalog."""

from __future__ import annotations

from dataclasses import dataclass


AWS_CURRENT_SESSION = "python_mcp.aws_sts:AwsStsClient.get_current_sts_session"
AWS_DESCRIBE_SESSION = "python_mcp.aws_sts:AwsStsClient.describe_session"
AWS_CALLER_IDENTITY = "python_mcp.aws_sts:AwsStsClient.get_caller_identity"
AWS_ASSUME_ROLE = "python_mcp.aws_sts:AwsStsClient.assume_role"
EMAIL_BUILD_MESSAGE = "python_mcp.emailer:EmailClient.build_message"
EMAIL_SEND = "python_mcp.emailer:EmailClient.send_email"


@dataclass(frozen=True)
class EvalCase:
    """A local effectiveness case for MCP discovery and catalog quality."""

    id: str
    language: str
    intent_group: str
    prompt: str
    expected_route: str
    expected_symbol_ids: tuple[str, ...] = ()
    forbidden_symbol_ids: tuple[str, ...] = ()
    expected_terms: tuple[str, ...] = ()
    requires_read_only_call: bool = False
    max_score: int = 10


EVAL_CASES: tuple[EvalCase, ...] = (
    EvalCase(
        id="aws_current_sts_session_zh",
        language="zh",
        intent_group="aws_sts",
        prompt="获取当前 AWS STS session 设置，包含当前 profile 和 region。",
        expected_route="python_mcp",
        expected_symbol_ids=(AWS_CURRENT_SESSION, AWS_DESCRIBE_SESSION),
        expected_terms=("profile_name", "region_name"),
        requires_read_only_call=True,
    ),
    EvalCase(
        id="aws_current_boto3_session_en",
        language="en",
        intent_group="aws_sts",
        prompt="Which helper should I use for current boto3 session settings?",
        expected_route="python_mcp",
        expected_symbol_ids=(AWS_CURRENT_SESSION, AWS_DESCRIBE_SESSION),
        expected_terms=("boto3", "session"),
        requires_read_only_call=True,
    ),
    EvalCase(
        id="aws_profile_region_zh",
        language="zh",
        intent_group="aws_sts",
        prompt="我想查看当前 boto3 profile 和 region，不要暴露 AWS credentials。",
        expected_route="python_mcp",
        expected_symbol_ids=(AWS_DESCRIBE_SESSION, AWS_CURRENT_SESSION),
        expected_terms=("profile_name", "region_name"),
        requires_read_only_call=True,
    ),
    EvalCase(
        id="aws_caller_identity_en",
        language="en",
        intent_group="aws_sts",
        prompt="Generate Python code to get AWS caller identity, account ID, and ARN.",
        expected_route="python_mcp",
        expected_symbol_ids=(AWS_CALLER_IDENTITY,),
        expected_terms=("account", "arn"),
        requires_read_only_call=False,
    ),
    EvalCase(
        id="aws_account_arn_zh",
        language="zh",
        intent_group="aws_sts",
        prompt="查询当前 AWS account ID 和 principal ARN，应该用哪个 helper？",
        expected_route="python_mcp",
        expected_symbol_ids=(AWS_CALLER_IDENTITY,),
        expected_terms=("account", "arn"),
        requires_read_only_call=False,
    ),
    EvalCase(
        id="aws_assume_role_preview_zh",
        language="zh",
        intent_group="aws_sts",
        prompt="我想 assume role 并预览 temporary credentials，不要直接暴露 secret。",
        expected_route="python_mcp",
        expected_symbol_ids=(AWS_ASSUME_ROLE,),
        expected_terms=("role_arn", "session_name"),
        requires_read_only_call=False,
    ),
    EvalCase(
        id="aws_assume_role_preview_en",
        language="en",
        intent_group="aws_sts",
        prompt="Find the helper for an assume-role temporary credentials preview.",
        expected_route="python_mcp",
        expected_symbol_ids=(AWS_ASSUME_ROLE,),
        expected_terms=("duration_seconds", "external_id"),
        requires_read_only_call=False,
    ),
    EvalCase(
        id="aws_sts_synonym_en",
        language="en",
        intent_group="aws_sts",
        prompt="How do I inspect the active STS helper session without raw boto3 calls?",
        expected_route="python_mcp",
        expected_symbol_ids=(AWS_CURRENT_SESSION, AWS_DESCRIBE_SESSION),
        expected_terms=("session", "boto3"),
        requires_read_only_call=True,
    ),
    EvalCase(
        id="email_mime_message_zh",
        language="zh",
        intent_group="email",
        prompt="构建 RFC 5322/MIME 邮件文本，收件人、主题和正文都要支持。",
        expected_route="python_mcp",
        expected_symbol_ids=(EMAIL_BUILD_MESSAGE,),
        expected_terms=("recipients", "subject", "body"),
        requires_read_only_call=True,
    ),
    EvalCase(
        id="email_html_body_zh",
        language="zh",
        intent_group="email",
        prompt="我需要生成带 HTML body 的 SMTP email message。",
        expected_route="python_mcp",
        expected_symbol_ids=(EMAIL_BUILD_MESSAGE, EMAIL_SEND),
        expected_terms=("html_body", "smtp"),
        requires_read_only_call=False,
    ),
    EvalCase(
        id="email_dry_run_preview_en",
        language="en",
        intent_group="email",
        prompt="Generate Python code to send a safe dry-run SMTP email preview.",
        expected_route="python_mcp",
        expected_symbol_ids=(EMAIL_SEND,),
        expected_terms=("dry_run", "recipients"),
        requires_read_only_call=False,
    ),
    EvalCase(
        id="email_smtp_config_zh",
        language="zh",
        intent_group="email",
        prompt="SMTP email 发送前，我想看 dry-run preview 和配置字段。",
        expected_route="python_mcp",
        expected_symbol_ids=(EMAIL_SEND,),
        expected_terms=("smtp_host", "dry_run"),
        requires_read_only_call=False,
    ),
    EvalCase(
        id="email_mime_synonym_en",
        language="en",
        intent_group="email",
        prompt="Which SDK method builds an RFC 5322 MIME message with optional HTML?",
        expected_route="python_mcp",
        expected_symbol_ids=(EMAIL_BUILD_MESSAGE,),
        expected_terms=("html_body", "recipients"),
        requires_read_only_call=True,
    ),
    EvalCase(
        id="email_send_synonym_en",
        language="en",
        intent_group="email",
        prompt="Find the send_email helper for an SMTP dry run.",
        expected_route="python_mcp",
        expected_symbol_ids=(EMAIL_SEND,),
        expected_terms=("dry_run", "sender"),
        requires_read_only_call=False,
    ),
    EvalCase(
        id="negative_csv_zh",
        language="zh",
        intent_group="none",
        prompt="用 Python 读取 CSV 并统计行数。",
        expected_route="none",
        forbidden_symbol_ids=(AWS_CURRENT_SESSION, AWS_CALLER_IDENTITY, EMAIL_SEND),
    ),
    EvalCase(
        id="negative_fastapi_zh",
        language="zh",
        intent_group="none",
        prompt="写一个 FastAPI health check endpoint。",
        expected_route="none",
        forbidden_symbol_ids=(AWS_CURRENT_SESSION, AWS_CALLER_IDENTITY, EMAIL_SEND),
    ),
    EvalCase(
        id="negative_json_en",
        language="en",
        intent_group="none",
        prompt="Parse a JSON file in Python and print each record.",
        expected_route="none",
        forbidden_symbol_ids=(AWS_CURRENT_SESSION, AWS_CALLER_IDENTITY, EMAIL_SEND),
    ),
    EvalCase(
        id="negative_calculator_test_en",
        language="en",
        intent_group="none",
        prompt="Write a unit test for a calculator add function.",
        expected_route="none",
        forbidden_symbol_ids=(AWS_CURRENT_SESSION, AWS_CALLER_IDENTITY, EMAIL_SEND),
    ),
)
