import pytest

from python_mcp.eval_cases import AWS_ASSUME_ROLE, EVAL_CASES
from python_mcp.eval_runner import run_eval
from python_mcp.mcp_catalog import CatalogError, CatalogIndex
from python_mcp.mcp_registry import PYTHON_MCP_CAPABILITIES
from python_mcp.mcp_server import SERVER_INSTRUCTIONS


def test_effectiveness_benchmark_meets_threshold() -> None:
    results = run_eval()

    total = sum(result.score for result in results)
    max_total = sum(result.max_score for result in results)
    failures = {
        result.case_id: result.failure_reasons
        for result in results
        if result.failure_reasons
    }

    assert total >= 150, failures
    assert max_total == 180


@pytest.mark.parametrize("result", run_eval())
def test_positive_cases_find_expected_symbols(result) -> None:
    if result.intent_group == "none":
        assert result.score == result.max_score
    else:
        assert result.search_score == 3, result
        assert result.detail_score == 2, result


def test_side_effect_symbol_requires_explicit_permission() -> None:
    catalog = CatalogIndex.build()

    with pytest.raises(CatalogError, match="allow_side_effects=True"):
        catalog.call_read_only_method(
            AWS_ASSUME_ROLE,
            kwargs={
                "role_arn": "arn:aws:iam::123456789012:role/Demo",
                "session_name": "demo",
            },
        )


def test_eval_cases_include_chinese_and_english_synonyms() -> None:
    languages_by_group: dict[str, set[str]] = {}
    for case in EVAL_CASES:
        languages_by_group.setdefault(case.intent_group, set()).add(case.language)

    assert languages_by_group["aws_sts"] == {"zh", "en"}
    assert languages_by_group["email"] == {"zh", "en"}
    assert languages_by_group["none"] == {"zh", "en"}


def test_discovery_text_supports_codex_tool_search() -> None:
    text = f"{SERVER_INSTRUCTIONS}\n{PYTHON_MCP_CAPABILITIES}".lower()

    for term in (
        "aws sts",
        "boto3 session",
        "smtp email",
        "mime",
        "rfc 5322",
        "dry-run",
        "imports the sdk directly",
    ):
        assert term in text
