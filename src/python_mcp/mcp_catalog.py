"""Griffe-backed symbol catalog for the MCP adapter."""

from __future__ import annotations

import importlib
import inspect
import json
import re
from dataclasses import dataclass
from typing import Any, get_type_hints

import griffe
from pydantic import BaseModel

from python_mcp.mcp_config import MCP_EXCLUDE_MODULE_PREFIXES, MCP_SCAN_PACKAGES
from python_mcp.mcp_factories import MCP_CLASS_FACTORIES

READ_ONLY_PREFIXES = (
    "get",
    "read",
    "list",
    "describe",
    "check",
    "validate",
    "build",
    "parse",
)


@dataclass(frozen=True)
class CatalogParameter:
    """A public method parameter indexed from source code."""

    name: str
    annotation: str
    default: str | None
    required: bool


@dataclass(frozen=True)
class CatalogSymbol:
    """A class method exposed through the indexed MCP catalog."""

    symbol_id: str
    module: str
    class_name: str
    method_name: str
    kind: str
    signature: str
    docstring: str
    return_type: str
    parameters: list[CatalogParameter]
    source_file: str | None
    safety: str
    tags: list[str]

    def summary(self) -> dict[str, Any]:
        """Return a compact search result representation."""

        return {
            "symbol_id": self.symbol_id,
            "module": self.module,
            "class_name": self.class_name,
            "method_name": self.method_name,
            "kind": self.kind,
            "signature": self.signature,
            "docstring": self.docstring,
            "safety": self.safety,
            "tags": self.tags,
        }

    def detail(self) -> dict[str, Any]:
        """Return the full symbol representation."""

        return {
            **self.summary(),
            "return_type": self.return_type,
            "parameters": [
                {
                    "name": parameter.name,
                    "annotation": parameter.annotation,
                    "default": parameter.default,
                    "required": parameter.required,
                }
                for parameter in self.parameters
            ],
            "source_file": self.source_file,
        }


class CatalogError(RuntimeError):
    """Raised when a catalog lookup or call fails."""


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


def _is_excluded_module(module_path: str) -> bool:
    return any(module_path.startswith(prefix) for prefix in MCP_EXCLUDE_MODULE_PREFIXES)


def _iter_modules_recursive(module: Any) -> list[Any]:
    modules: list[Any] = []
    for child in module.modules.values():
        modules.append(child)
        modules.extend(_iter_modules_recursive(child))
    return modules


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


def _source_file(module: Any) -> str | None:
    filepath = getattr(module, "filepath", None)
    if filepath is not None:
        return str(filepath)
    path = getattr(module, "file_path", None)
    if path is not None:
        return str(path)
    return None


def _annotation_text(value: Any) -> str:
    if value is inspect.Signature.empty:
        return "Any"
    text = str(value)
    text = text.replace("<class '", "").replace("'>", "")
    return text


def _safety(method_name: str) -> str:
    if method_name.startswith(READ_ONLY_PREFIXES):
        return "read_only"
    return "unknown"


def _tags(module_path: str, class_name: str, method_name: str, docstring: str) -> list[str]:
    text = f"{module_path} {class_name} {method_name} {docstring}".lower()
    candidates = {
        "aws": ["aws", "boto3"],
        "sts": ["sts", "assume role", "assume-role", "caller identity"],
        "email": ["email", "smtp", "message"],
        "mime": ["mime", "rfc 5322", "rfc5322", "html"],
        "dry-run": ["dry-run", "dry_run", "preview"],
        "config": ["config", "environment"],
        "identity": ["identity", "account", "account id", "arn"],
        "credentials": ["credentials", "temporary credentials", "session token"],
    }
    tags = [
        tag
        for tag, markers in candidates.items()
        if any(marker in text for marker in markers)
    ]
    return tags or ["python"]


def _load_runtime_method(module_path: str, class_name: str, method_name: str) -> Any:
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    method = getattr(cls, method_name)
    if not callable(method):
        raise CatalogError(f"{module_path}.{class_name}.{method_name} is not callable")
    return method


def _runtime_signature(module_path: str, class_name: str, method_name: str) -> inspect.Signature:
    method = _load_runtime_method(module_path, class_name, method_name)
    signature = inspect.signature(method)
    type_hints = get_type_hints(method)
    parameters = [
        parameter.replace(annotation=type_hints.get(parameter.name, parameter.annotation))
        for parameter in signature.parameters.values()
        if parameter.name != "self"
    ]
    return_annotation = type_hints.get("return", signature.return_annotation)
    return inspect.Signature(parameters=parameters, return_annotation=return_annotation)


class CatalogIndex:
    """Searchable index of public methods discovered by Griffe."""

    def __init__(self, symbols: list[CatalogSymbol]) -> None:
        self._symbols = symbols
        self._by_id = {symbol.symbol_id: symbol for symbol in symbols}

    @classmethod
    def build(cls) -> "CatalogIndex":
        """Build a catalog from configured packages."""

        symbols: list[CatalogSymbol] = []
        for package_name in MCP_SCAN_PACKAGES:
            package = griffe.load(package_name)
            for module in _iter_modules_recursive(package):
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
                        docstring = _method_description(method_obj, method_name)
                        signature = _runtime_signature(module_path, class_name, method_name)
                        parameters = [
                            CatalogParameter(
                                name=parameter.name,
                                annotation=_annotation_text(parameter.annotation),
                                default=None
                                if parameter.default is inspect.Parameter.empty
                                else repr(parameter.default),
                                required=parameter.default is inspect.Parameter.empty,
                            )
                            for parameter in signature.parameters.values()
                        ]
                        symbols.append(
                            CatalogSymbol(
                                symbol_id=f"{module_path}:{class_name}.{method_name}",
                                module=module_path,
                                class_name=class_name,
                                method_name=method_name,
                                kind="method",
                                signature=str(signature),
                                docstring=docstring,
                                return_type=_annotation_text(signature.return_annotation),
                                parameters=parameters,
                                source_file=_source_file(module),
                                safety=_safety(method_name),
                                tags=_tags(module_path, class_name, method_name, docstring),
                            )
                        )
        return cls(symbols)

    def list_modules(self) -> list[dict[str, Any]]:
        """List indexed modules and symbol counts."""

        counts: dict[str, int] = {}
        for symbol in self._symbols:
            counts[symbol.module] = counts.get(symbol.module, 0) + 1
        return [
            {"module": module, "symbol_count": count}
            for module, count in sorted(counts.items())
        ]

    def search(
        self,
        query: str,
        module: str | None = None,
        kind: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search symbols by name, signature, docstring, and tags."""

        terms = [term for term in re.split(r"\s+", query.lower().strip()) if term]
        scored: list[tuple[int, CatalogSymbol]] = []
        for symbol in self._symbols:
            if module and symbol.module != module:
                continue
            if kind and symbol.kind != kind:
                continue
            haystack = " ".join(
                [
                    symbol.symbol_id,
                    symbol.module,
                    symbol.class_name,
                    symbol.method_name,
                    symbol.signature,
                    symbol.docstring,
                    " ".join(symbol.tags),
                ]
            ).lower()
            if not terms:
                score = 1
            else:
                score = sum(1 for term in terms if term in haystack)
            if score:
                scored.append((score, symbol))
        scored.sort(key=lambda item: (-item[0], item[1].symbol_id))
        return [symbol.summary() for _, symbol in scored[: max(limit, 1)]]

    def detail(self, symbol_id: str) -> dict[str, Any]:
        """Return details for a symbol ID."""

        symbol = self._by_id.get(symbol_id)
        if symbol is None:
            raise CatalogError(f"unknown symbol_id: {symbol_id}")
        return symbol.detail()

    def call_method(
        self,
        symbol_id: str,
        kwargs: dict[str, Any] | None = None,
        allow_side_effects: bool = False,
    ) -> Any:
        """Call an indexed method by symbol ID."""

        symbol = self._by_id.get(symbol_id)
        if symbol is None:
            raise CatalogError(f"unknown symbol_id: {symbol_id}")
        if symbol.kind != "method":
            raise CatalogError(f"symbol is not callable: {symbol_id}")
        if symbol.safety != "read_only" and not allow_side_effects:
            raise CatalogError(
                f"{symbol_id} has safety={symbol.safety}; pass allow_side_effects=True to call it"
            )

        dotted_class = f"{symbol.module}.{symbol.class_name}"
        factory = MCP_CLASS_FACTORIES.get(dotted_class)
        if factory is None:
            cls = getattr(importlib.import_module(symbol.module), symbol.class_name)
            instance = cls()
        else:
            instance = factory()
        result = getattr(instance, symbol.method_name)(**(kwargs or {}))
        return _jsonable(result)

    def call_read_only_method(
        self,
        symbol_id: str,
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        """Call an indexed method only when it is classified as read-only."""

        return self.call_method(
            symbol_id=symbol_id,
            kwargs=kwargs,
            allow_side_effects=False,
        )
