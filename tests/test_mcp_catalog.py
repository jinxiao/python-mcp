import pytest

from python_mcp.mcp_catalog import CatalogError, CatalogIndex


def test_catalog_search_finds_sts_methods() -> None:
    catalog = CatalogIndex.build()

    results = catalog.search("aws sts session")
    symbol_ids = {result["symbol_id"] for result in results}

    assert "python_mcp.aws_sts:AwsStsClient.describe_session" in symbol_ids


def test_catalog_search_finds_current_sts_session_helper() -> None:
    catalog = CatalogIndex.build()

    results = catalog.search("get current sts session")
    symbol_ids = [result["symbol_id"] for result in results]

    assert "python_mcp.aws_sts:AwsStsClient.get_current_sts_session" in symbol_ids


def test_catalog_search_finds_email_api_doc_terms() -> None:
    catalog = CatalogIndex.build()

    results = catalog.search("smtp dry run preview send email")
    symbol_ids = [result["symbol_id"] for result in results]

    assert "python_mcp.emailer:EmailClient.send_email" in symbol_ids


def test_catalog_detail_contains_signature_and_safety() -> None:
    catalog = CatalogIndex.build()

    detail = catalog.detail("python_mcp.emailer:EmailClient.build_message")

    assert detail["method_name"] == "build_message"
    assert detail["safety"] == "read_only"
    assert "recipients" in detail["signature"]


def test_catalog_detail_supports_direct_import_codegen() -> None:
    catalog = CatalogIndex.build()

    detail = catalog.detail("python_mcp.emailer:EmailClient.build_message")

    assert detail["module"] == "python_mcp.emailer"
    assert detail["class_name"] == "EmailClient"
    assert detail["method_name"] == "build_message"
    assert detail["return_type"] == "str"
    assert "RFC 5322/MIME" in detail["docstring"]
    assert detail["source_file"] is not None


def test_catalog_call_allows_read_only_method() -> None:
    catalog = CatalogIndex.build()

    result = catalog.call_method(
        "python_mcp.emailer:EmailClient.build_message",
        kwargs={
            "sender": "from@example.com",
            "recipients": ["to@example.com"],
            "subject": "Hello",
            "body": "Plain body",
        },
    )

    assert "Subject: Hello" in result


def test_catalog_call_current_sts_session_helper() -> None:
    catalog = CatalogIndex.build()

    result = catalog.call_read_only_method(
        "python_mcp.aws_sts:AwsStsClient.get_current_sts_session"
    )

    assert set(result) == {"profile_name", "region_name"}


def test_catalog_read_only_call_allows_only_read_only_method() -> None:
    catalog = CatalogIndex.build()

    result = catalog.call_read_only_method(
        "python_mcp.emailer:EmailClient.build_message",
        kwargs={
            "sender": "from@example.com",
            "recipients": ["to@example.com"],
            "subject": "Hello",
            "body": "Plain body",
        },
    )

    assert "Subject: Hello" in result

    with pytest.raises(CatalogError, match="allow_side_effects=True"):
        catalog.call_read_only_method(
            "python_mcp.aws_sts:AwsStsClient.assume_role",
            kwargs={
                "role_arn": "arn:aws:iam::123456789012:role/Demo",
                "session_name": "demo",
            },
        )


def test_catalog_call_rejects_unknown_safety_by_default() -> None:
    catalog = CatalogIndex.build()

    with pytest.raises(CatalogError, match="allow_side_effects=True"):
        catalog.call_method(
            "python_mcp.aws_sts:AwsStsClient.assume_role",
            kwargs={
                "role_arn": "arn:aws:iam::123456789012:role/Demo",
                "session_name": "demo",
            },
        )
