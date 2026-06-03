"""Runtime Griffe scanner and FastMCP registration helpers."""

from __future__ import annotations

import importlib
import inspect
import json
import re
from collections.abc import Callable
from functools import wraps
from typing import Any, get_type_hints

import griffe
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel

from python_mcp.mcp_catalog import READ_ONLY_PREFIXES, CatalogIndex
from python_mcp.mcp_config import (
    MCP_EXCLUDE_MODULE_PREFIXES,
    MCP_REGISTER_METHOD_TOOLS,
    MCP_SCAN_PACKAGES,
)
from python_mcp.mcp_factories import MCP_CLASS_FACTORIES


PYTHON_MCP_CAPABILITIES = (
    "python-mcp is a Griffe-indexed public Python helper library. Use MCP as a "
    "searchable API catalog for agents, then generate ordinary Python code that "
    "imports the SDK directly. It currently covers AWS STS and boto3 session "
    "helpers such as current STS session, current boto3 session settings, get "
    "caller identity, AWS account ID, ARN, assume role, temporary credentials "
    "preview, and session settings; it also covers SMTP email helpers such as "
    "RFC 5322/MIME message building, HTML email body generation, dry-run "
    "send_email previews, and SMTP send configuration."
)

READ_ONLY_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
READ_ONLY_RUNTIME_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
SIDE_EFFECT_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=False,
    openWorldHint=True,
)


class ToolRegistrationError(RuntimeError):
    """Raised when an MCP tool cannot be registered."""


def _is_excluded_module(module_path: str) -> bool:
    return any(module_path.startswith(prefix) for prefix in MCP_EXCLUDE_MODULE_PREFIXES)


def _tool_name(module_path: str, class_name: str, method_name: str) -> str:
    parts = [_snake(part) for part in module_path.split(".")]
    parts.extend([_snake(class_name), _snake(method_name)])
    return "_".join(part for part in parts if part)


def _snake(value: str) -> str:
    value = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value)
    return value.strip("_").lower()


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value


def _method_description(method: Any, method_name: str) -> str:
    docstring = getattr(method, "docstring", None)
    if docstring:
        parsed = docstring.parsed
        if parsed:
            text = "\n".join(
                str(getattr(part, "value", part)).strip()
                for part in parsed
                if str(getattr(part, "value", part)).strip()
            )
            if text:
                return text
        if docstring.value:
            return docstring.value.strip()
    return f"Call public method `{method_name}` from the Python library."


def _load_runtime_method(module_path: str, class_name: str, method_name: str) -> Callable[..., Any]:
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    method = getattr(cls, method_name)
    if not callable(method):
        raise ToolRegistrationError(f"{module_path}.{class_name}.{method_name} is not callable")
    return method


def _iter_modules_recursive(module: Any) -> list[Any]:
    modules: list[Any] = []
    for child in module.modules.values():
        modules.append(child)
        modules.extend(_iter_modules_recursive(child))
    return modules


def _make_tool(
    module_path: str,
    class_name: str,
    method_name: str,
    description: str,
) -> Callable[..., Any]:
    dotted_class = f"{module_path}.{class_name}"
    method = _load_runtime_method(module_path, class_name, method_name)
    signature = inspect.signature(method)
    type_hints = get_type_hints(method)
    parameters = [
        parameter.replace(annotation=type_hints.get(parameter.name, parameter.annotation))
        for parameter in signature.parameters.values()
        if parameter.name != "self"
    ]
    public_signature = inspect.Signature(
        parameters=parameters,
        return_annotation=Any,
    )

    annotations = {
        name: hint
        for name, hint in type_hints.items()
        if name != "return"
    }
    annotations["return"] = Any

    @wraps(method)
    def tool(**kwargs: Any) -> Any:
        factory = MCP_CLASS_FACTORIES.get(dotted_class)
        if factory is None:
            cls = getattr(importlib.import_module(module_path), class_name)
            instance = cls()
        else:
            instance = factory()
        result = getattr(instance, method_name)(**kwargs)
        return _jsonable(result)

    tool.__name__ = _tool_name(module_path, class_name, method_name)
    tool.__qualname__ = tool.__name__
    tool.__doc__ = description
    tool.__signature__ = public_signature
    tool.__annotations__ = annotations
    return tool


def _is_read_only_method(method_name: str) -> bool:
    return method_name.startswith(READ_ONLY_PREFIXES)


def iter_public_methods() -> list[tuple[str, str, str, str]]:
    """Return public methods discovered from configured packages."""

    discovered: list[tuple[str, str, str, str]] = []
    for package_name in MCP_SCAN_PACKAGES:
        package = griffe.load(package_name)
        modules = _iter_modules_recursive(package)
        for module in modules:
            module_path = module.path
            if _is_excluded_module(module_path):
                continue
            for class_name, class_obj in module.classes.items():
                if class_name.startswith("_"):
                    continue
                if getattr(class_obj, "is_alias", False):
                    continue
                for method_name, method_obj in class_obj.functions.items():
                    if method_name.startswith("_"):
                        continue
                    description = _method_description(method_obj, method_name)
                    discovered.append((module_path, class_name, method_name, description))
    return discovered


def register_griffe_tools(mcp: FastMCP) -> list[str]:
    """Register Griffe-discovered public methods as FastMCP tools."""

    names: list[str] = []
    used: set[str] = set()
    for module_path, class_name, method_name, description in iter_public_methods():
        tool = _make_tool(module_path, class_name, method_name, description)
        if tool.__name__ in used:
            raise ToolRegistrationError(f"duplicate MCP tool name: {tool.__name__}")
        used.add(tool.__name__)
        annotations = (
            READ_ONLY_RUNTIME_ANNOTATIONS
            if _is_read_only_method(method_name)
            else SIDE_EFFECT_TOOL_ANNOTATIONS
        )
        mcp.tool(
            name=tool.__name__,
            description=description,
            annotations=annotations,
        )(tool)
        names.append(tool.__name__)
    return names


def register_catalog_tools(mcp: FastMCP, catalog: CatalogIndex) -> list[str]:
    """Register a small set of catalog tools for large public libraries."""

    @mcp.tool(
        name="python_mcp_list_modules",
        description=(
            "List modules indexed by python-mcp. "
            f"{PYTHON_MCP_CAPABILITIES}"
        ),
        annotations=READ_ONLY_TOOL_ANNOTATIONS,
    )
    def list_modules() -> list[dict[str, Any]]:
        return catalog.list_modules()

    @mcp.tool(
        name="python_mcp_search_symbols",
        description=(
            "Search python-mcp symbols by natural language query, module, kind, "
            "and tags. Use this first before writing raw boto3 or smtplib code "
            "for requests involving AWS STS, current STS session, current boto3 "
            "session settings, caller identity, AWS account or ARN lookup, "
            "assume-role sessions, temporary credential previews, SMTP email, "
            "MIME/RFC 5322 message building, HTML email, dry-run email previews, "
            "or send_email helpers. "
            f"{PYTHON_MCP_CAPABILITIES}"
        ),
        annotations=READ_ONLY_TOOL_ANNOTATIONS,
    )
    def search_symbols(
        query: str,
        module: str | None = None,
        kind: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        return catalog.search(query=query, module=module, kind=kind, limit=limit)

    @mcp.tool(
        name="python_mcp_get_symbol_detail",
        description=(
            "Return full signature, parameters, docstring, safety, and source "
            "metadata for a python-mcp symbol found by python_mcp_search_symbols. "
            "Use this before generating direct Python imports or calling AWS STS "
            "and SMTP email helper methods."
        ),
        annotations=READ_ONLY_TOOL_ANNOTATIONS,
    )
    def get_symbol_detail(symbol_id: str) -> dict[str, Any]:
        return catalog.detail(symbol_id)

    @mcp.tool(
        name="python_mcp_call_read_only_method",
        description=(
            "Call an indexed python-mcp method only when its safety metadata is "
            "read_only. Use this for runtime confirmation that should not modify "
            "state or require side-effect approval."
        ),
        annotations=READ_ONLY_RUNTIME_ANNOTATIONS,
    )
    def call_read_only_method(
        symbol_id: str,
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        return catalog.call_read_only_method(
            symbol_id=symbol_id,
            kwargs=kwargs,
        )

    @mcp.tool(
        name="python_mcp_call_method",
        description=(
            "Call an indexed python-mcp method by symbol_id for runtime "
            "confirmation when side effects are explicitly allowed. Prefer "
            "python_mcp_call_read_only_method for read-only calls. Non-read-only "
            "methods require allow_side_effects=true."
        ),
        annotations=SIDE_EFFECT_TOOL_ANNOTATIONS,
    )
    def call_method(
        symbol_id: str,
        kwargs: dict[str, Any] | None = None,
        allow_side_effects: bool = False,
    ) -> Any:
        return catalog.call_method(
            symbol_id=symbol_id,
            kwargs=kwargs,
            allow_side_effects=allow_side_effects,
        )

    return [
        "python_mcp_list_modules",
        "python_mcp_search_symbols",
        "python_mcp_get_symbol_detail",
        "python_mcp_call_read_only_method",
        "python_mcp_call_method",
    ]


def register_mcp_tools(mcp: FastMCP) -> list[str]:
    """Register default MCP tools.

    Catalog tools are always registered. Per-method tools are opt-in through
    PYTHON_MCP_REGISTER_METHOD_TOOLS=true.
    """

    catalog = CatalogIndex.build()
    names = register_catalog_tools(mcp, catalog)
    if MCP_REGISTER_METHOD_TOOLS:
        names.extend(register_griffe_tools(mcp))
    return names
