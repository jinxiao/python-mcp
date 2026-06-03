"""Local effectiveness runner for the python-mcp MCP catalog."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Any

from python_mcp.eval_cases import AWS_ASSUME_ROLE, EMAIL_BUILD_MESSAGE, EvalCase, EVAL_CASES
from python_mcp.mcp_catalog import CatalogError, CatalogIndex


TOP_K = 5


@dataclass(frozen=True)
class EvalResult:
    """Scored result for one effectiveness case."""

    case_id: str
    language: str
    intent_group: str
    score: int
    max_score: int
    route_score: int
    search_score: int
    detail_score: int
    safety_score: int
    import_score: int
    selected_symbol_ids: tuple[str, ...]
    failure_reasons: tuple[str, ...]


ROUTE_MARKERS = (
    "arn",
    "assume role",
    "assume-role",
    "aws",
    "boto3",
    "caller identity",
    "dry-run",
    "email",
    "html body",
    "mime",
    "principal",
    "rfc 5322",
    "send_email",
    "smtp",
    "sts",
    "temporary credentials",
    "邮件",
    "凭证",
    "发送",
    "账号",
    "配置",
)


def _should_route_to_python_mcp(prompt: str) -> bool:
    text = prompt.lower()
    return any(marker in text for marker in ROUTE_MARKERS)


def _safe_search(catalog: CatalogIndex, prompt: str) -> list[dict[str, Any]]:
    if not _should_route_to_python_mcp(prompt):
        return []
    return catalog.search(query=prompt, limit=TOP_K)


def _has_any_symbol(symbol_ids: tuple[str, ...], expected: tuple[str, ...]) -> bool:
    return any(symbol_id in symbol_ids for symbol_id in expected)


def _detail_is_complete(detail: dict[str, Any]) -> bool:
    required_fields = ("module", "class_name", "method_name", "signature", "safety")
    return all(detail.get(field) for field in required_fields)


def _direct_import_from_detail(detail: dict[str, Any]) -> str:
    return f"from {detail['module']} import {detail['class_name']}"


def _score_positive_case(
    catalog: CatalogIndex,
    case: EvalCase,
    selected_symbol_ids: tuple[str, ...],
) -> tuple[int, int, int, int, int, list[str]]:
    failures: list[str] = []
    route_score = 2 if selected_symbol_ids else 0
    if not route_score:
        failures.append("no python_mcp catalog results")

    search_hit = _has_any_symbol(selected_symbol_ids, case.expected_symbol_ids)
    search_score = 3 if search_hit else 0
    if not search_hit:
        failures.append("expected symbol not found in top results")
        return route_score, search_score, 0, 0, 0, failures

    selected = next(
        symbol_id
        for symbol_id in selected_symbol_ids
        if symbol_id in case.expected_symbol_ids
    )
    detail = catalog.detail(selected)
    detail_score = 2 if _detail_is_complete(detail) else 0
    if not detail_score:
        failures.append("symbol detail is missing required fields")

    safety_score = _score_safety(catalog, selected, case.requires_read_only_call)
    if not safety_score:
        failures.append("read-only or side-effect safety behavior failed")

    import_score = 1 if _direct_import_from_detail(detail).startswith("from python_mcp.") else 0
    if not import_score:
        failures.append("symbol detail does not support direct SDK import generation")

    return route_score, search_score, detail_score, safety_score, import_score, failures


def _score_negative_case(
    case: EvalCase,
    selected_symbol_ids: tuple[str, ...],
) -> tuple[int, int, int, int, int, list[str]]:
    failures: list[str] = []
    forbidden_hit = _has_any_symbol(selected_symbol_ids, case.forbidden_symbol_ids)
    if forbidden_hit:
        failures.append("negative prompt matched a forbidden python_mcp symbol")
        return 0, 0, 2, 2, 1, failures
    return 2, 3, 2, 2, 1, failures


def _score_safety(
    catalog: CatalogIndex,
    selected_symbol_id: str,
    requires_read_only_call: bool,
) -> int:
    if requires_read_only_call:
        kwargs: dict[str, Any] | None = None
        if selected_symbol_id == EMAIL_BUILD_MESSAGE:
            kwargs = {
                "sender": "from@example.com",
                "recipients": ["to@example.com"],
                "subject": "Hello",
                "body": "Plain body",
            }
        try:
            catalog.call_read_only_method(selected_symbol_id, kwargs=kwargs)
        except Exception:
            return 0
        return 2

    if selected_symbol_id == AWS_ASSUME_ROLE:
        try:
            catalog.call_read_only_method(
                selected_symbol_id,
                kwargs={
                    "role_arn": "arn:aws:iam::123456789012:role/Demo",
                    "session_name": "demo",
                },
            )
        except CatalogError:
            return 2
        return 0

    detail = catalog.detail(selected_symbol_id)
    return 2 if detail["safety"] in {"read_only", "unknown"} else 0


def score_case(catalog: CatalogIndex, case: EvalCase) -> EvalResult:
    """Score one case against the local catalog implementation."""

    results = _safe_search(catalog, case.prompt)
    selected_symbol_ids = tuple(result["symbol_id"] for result in results)
    if case.expected_route == "none":
        scores = _score_negative_case(case, selected_symbol_ids)
    else:
        scores = _score_positive_case(catalog, case, selected_symbol_ids)

    route_score, search_score, detail_score, safety_score, import_score, failures = scores
    score = route_score + search_score + detail_score + safety_score + import_score
    return EvalResult(
        case_id=case.id,
        language=case.language,
        intent_group=case.intent_group,
        score=score,
        max_score=case.max_score,
        route_score=route_score,
        search_score=search_score,
        detail_score=detail_score,
        safety_score=safety_score,
        import_score=import_score,
        selected_symbol_ids=selected_symbol_ids,
        failure_reasons=tuple(failures),
    )


def run_eval(case_id: str | None = None) -> list[EvalResult]:
    """Run the local effectiveness benchmark."""

    catalog = CatalogIndex.build()
    cases = EVAL_CASES
    if case_id:
        cases = tuple(case for case in EVAL_CASES if case.id == case_id)
        if not cases:
            raise SystemExit(f"unknown eval case: {case_id}")
    return [score_case(catalog, case) for case in cases]


def _print_table(results: list[EvalResult]) -> None:
    print("case_id | lang | group | score | failures")
    print("--- | --- | --- | ---: | ---")
    for result in results:
        failures = "; ".join(result.failure_reasons) if result.failure_reasons else "-"
        print(
            f"{result.case_id} | {result.language} | {result.intent_group} | "
            f"{result.score}/{result.max_score} | {failures}"
        )
    total = sum(result.score for result in results)
    max_total = sum(result.max_score for result in results)
    print(f"\nTotal: {total}/{max_total}")


def _as_json(results: list[EvalResult]) -> str:
    total = sum(result.score for result in results)
    max_total = sum(result.max_score for result in results)
    payload = {
        "total_score": total,
        "max_score": max_total,
        "results": [asdict(result) for result in results],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", help="Run a single eval case by id.")
    parser.add_argument(
        "--format",
        choices=("table", "json"),
        default="table",
        help="Output format.",
    )
    args = parser.parse_args()

    results = run_eval(case_id=args.case)
    if args.format == "json":
        print(_as_json(results))
    else:
        _print_table(results)


if __name__ == "__main__":
    main()
