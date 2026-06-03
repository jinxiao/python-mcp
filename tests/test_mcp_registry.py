from python_mcp.mcp_catalog import CatalogIndex
from python_mcp.mcp_registry import (
    iter_public_methods,
    register_catalog_tools,
    register_griffe_tools,
)


class FakeMcp:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}

    def tool(self, name: str, description: str, annotations=None):
        def decorator(func):
            self.tools[name] = {
                "description": description,
                "annotations": annotations,
                "func": func,
            }
            return func

        return decorator


def test_griffe_discovers_public_methods() -> None:
    methods = iter_public_methods()
    method_names = {(module, cls, method) for module, cls, method, _ in methods}

    assert ("python_mcp.aws_sts", "AwsStsClient", "get_caller_identity") in method_names
    assert ("python_mcp.aws_sts", "AwsStsClient", "get_current_sts_session") in method_names
    assert ("python_mcp.emailer", "EmailClient", "build_message") in method_names
    assert all(not method.startswith("_") for _, _, method, _ in methods)


def test_register_griffe_tools_uses_stable_names() -> None:
    fake = FakeMcp()

    names = register_griffe_tools(fake)

    assert "python_mcp_aws_sts_aws_sts_client_get_caller_identity" in names
    assert "python_mcp_aws_sts_aws_sts_client_get_current_sts_session" in names
    assert "python_mcp_emailer_email_client_build_message" in names
    assert set(names) == set(fake.tools)
    assert (
        fake.tools[
            "python_mcp_aws_sts_aws_sts_client_get_caller_identity"
        ]["annotations"].readOnlyHint
        is True
    )
    assert (
        fake.tools[
            "python_mcp_aws_sts_aws_sts_client_assume_role"
        ]["annotations"].readOnlyHint
        is False
    )


def test_register_catalog_tools_uses_fixed_names() -> None:
    fake = FakeMcp()
    catalog = CatalogIndex.build()

    names = register_catalog_tools(fake, catalog)

    assert names == [
        "python_mcp_list_modules",
        "python_mcp_search_symbols",
        "python_mcp_get_symbol_detail",
        "python_mcp_call_read_only_method",
        "python_mcp_call_method",
    ]
    assert set(names) == set(fake.tools)
    assert fake.tools["python_mcp_list_modules"]["annotations"].readOnlyHint is True
    assert fake.tools["python_mcp_search_symbols"]["annotations"].readOnlyHint is True
    assert fake.tools["python_mcp_get_symbol_detail"]["annotations"].readOnlyHint is True
    assert fake.tools["python_mcp_call_read_only_method"]["annotations"].readOnlyHint is True
    assert fake.tools["python_mcp_call_method"]["annotations"].readOnlyHint is False


def test_catalog_tool_descriptions_include_discovery_terms() -> None:
    fake = FakeMcp()
    catalog = CatalogIndex.build()

    register_catalog_tools(fake, catalog)

    search_description = fake.tools["python_mcp_search_symbols"]["description"]
    assert "AWS STS" in search_description
    assert "SMTP email" in search_description
    assert "current STS session" in search_description
    assert "raw boto3" in search_description
    assert "caller identity" in search_description
    assert "MIME/RFC 5322" in search_description
    assert "imports the SDK directly" in search_description

    detail_description = fake.tools["python_mcp_get_symbol_detail"]["description"]
    assert "direct Python imports" in detail_description
