"""Assemble a surface inventory from declared records or a narrow source subset.

Python extraction uses the standard library parser and does not execute the
file. JavaScript extraction only recognizes ipcMain.handle callbacks whose
parameters are a comma-separated identifier list. Class methods, other
languages, and destructured callbacks are outside this subset.
"""

import ast
import re
from pathlib import PurePosixPath

from app.core.errors import CatalogError
from app.core.naming import is_ident, normalize_type, slug

MAX_SURFACES = 200
MAX_FILES = 40
MAX_SOURCE_CHARS = 100_000
ROUTE_RECEIVERS = {"app", "router", "api"}
ROUTE_METHODS = {"get", "post", "put", "patch", "delete"}
JS_SUFFIXES = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
IPC_LOOSE = re.compile(
    r"ipcMain\.handle\(\s*(['\"])(?P<channel>[A-Za-z0-9_.:-]+)\1",
)
IPC_STRICT = re.compile(
    r"ipcMain\.handle\(\s*(['\"])(?P<channel>[A-Za-z0-9_.:-]+)\1\s*,\s*"
    r"(?:async\s*)?(?:function\s*)?\(\s*event\s*"
    r"(?:,\s*(?P<args>[A-Za-z0-9_,\s]*))?\)",
)


def assemble_inventory(payload: object) -> dict:
    """Validate a request body and return application, surfaces, and notices."""
    if not isinstance(payload, dict):
        raise CatalogError("inventory must be an object", "inventory")
    application = _string(payload.get("application"), "application", 80)
    executable_name = slug(application)
    if not is_ident(executable_name):
        raise CatalogError(
            "application name cannot form a command name",
            "application",
        )
    has_surfaces = "surfaces" in payload
    has_files = "files" in payload
    if not has_surfaces and not has_files:
        raise CatalogError("provide surfaces or files", "inventory")

    surfaces: list[dict] = []
    notices: list[str] = []
    if has_files:
        surfaces.extend(_surfaces_from_files(payload.get("files"), notices))
    if has_surfaces:
        surfaces.extend(_declared_surfaces(payload.get("surfaces")))
    if len(surfaces) > MAX_SURFACES:
        raise CatalogError("too many surfaces", "surfaces")
    _reject_duplicate_ids(surfaces)
    return {
        "application": application,
        "executable_name": executable_name,
        "surfaces": surfaces,
        "notices": notices,
    }


def _declared_surfaces(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        raise CatalogError("surfaces must be a list", "surfaces")
    surfaces = []
    for index, item in enumerate(raw):
        field = f"surfaces[{index}]"
        if not isinstance(item, dict):
            raise CatalogError("surface must be an object", field)
        surfaces.append(normalize_surface(item, field))
    return surfaces


def _surfaces_from_files(raw: object, notices: list[str]) -> list[dict]:
    if not isinstance(raw, list):
        raise CatalogError("files must be a list", "files")
    if len(raw) > MAX_FILES:
        raise CatalogError("too many files", "files")
    surfaces: list[dict] = []
    for index, item in enumerate(raw):
        field = f"files[{index}]"
        if not isinstance(item, dict):
            raise CatalogError("file must be an object", field)
        path = _relative_path(item.get("path"), f"{field}.path")
        source = _string(item.get("source"), f"{field}.source", MAX_SOURCE_CHARS, allow_empty=True)
        if "\x00" in source:
            raise CatalogError("source must be text", f"{field}.source")
        suffix = PurePosixPath(path).suffix.lower()
        before = len(surfaces)
        if suffix == ".py":
            surfaces.extend(_python_file(path, source, field))
        elif suffix in JS_SUFFIXES:
            surfaces.extend(_javascript_file(path, source, field, notices))
        else:
            raise CatalogError("unsupported file type", f"{field}.path")
        if len(surfaces) == before:
            notices.append(f"{path} contributed no supported surfaces")
    return surfaces


def normalize_surface(raw: dict, field: str) -> dict:
    identifier = _string(raw.get("id"), f"{field}.id", 160)
    kind = _optional_string(raw.get("kind"), f"{field}.kind", 32).lower()
    module = _optional_string(raw.get("module"), f"{field}.module", 80)
    handler = _optional_string(raw.get("handler"), f"{field}.handler", 80)
    summary = _optional_string(raw.get("summary"), f"{field}.summary", 400)
    method = _optional_method(raw.get("method"), f"{field}.method")
    route = _optional_string(raw.get("path"), f"{field}.path", 200)
    params = _normalize_params(raw.get("params", []), f"{field}.params")
    defects = raw.get("defects") or []
    if not isinstance(defects, list) or any(not isinstance(item, str) for item in defects):
        raise CatalogError("defects must be a list of strings", f"{field}.defects")
    return {
        "id": identifier,
        "kind": kind,
        "module": module,
        "handler": handler,
        "summary": summary,
        "method": method,
        "path": route or None,
        "params": params,
        "defects": list(defects),
    }


def _normalize_params(raw: object, field: str) -> list[dict]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise CatalogError("params must be a list", field)
    if len(raw) > 30:
        raise CatalogError("too many parameters", field)
    params = []
    for index, item in enumerate(raw):
        item_field = f"{field}[{index}]"
        if not isinstance(item, dict):
            raise CatalogError("parameter must be an object", item_field)
        name = _string(item.get("name"), f"{item_field}.name", 64)
        type_name = normalize_type(_optional_string(item.get("type"), f"{item_field}.type", 32) or "string")
        required = item.get("required", True)
        if not isinstance(required, bool):
            raise CatalogError("expected a boolean", f"{item_field}.required")
        params.append(
            {
                "name": name,
                "type": type_name,
                "required": required,
                "flag": slug(name),
            }
        )
    return params


def _python_file(path: str, source: str, field: str) -> list[dict]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        line = exc.lineno or 0
        raise CatalogError(
            f"python syntax error on line {line}: {exc.msg}",
            f"{field}.source",
        ) from exc
    stem = PurePosixPath(path).stem
    surfaces = []
    seen: dict[str, int] = {}
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_"):
            continue
        seen[node.name] = seen.get(node.name, 0) + 1
        suffix = "" if seen[node.name] == 1 else f"#{seen[node.name]}"
        route_method, route_path, route_defects = _python_route(node)
        defects = list(route_defects)
        if node.args.vararg or node.args.kwarg:
            defects.append("variadic parameters are not bound")
        surfaces.append(
            normalize_surface(
                {
                    "id": f"{path}::{node.name}{suffix}",
                    "kind": "http" if route_method else "function",
                    "module": stem,
                    "handler": node.name,
                    "summary": _docstring(node),
                    "method": route_method,
                    "path": route_path,
                    "params": _python_params(node),
                    "defects": defects,
                },
                field,
            )
        )
    return surfaces


def _python_route(node: ast.AST) -> tuple[str | None, str | None, list[str]]:
    found: list[tuple[str, str]] = []
    for decorator in node.decorator_list:
        parsed = _route_decorator(decorator)
        if parsed is not None:
            found.append(parsed)
    if not found:
        return None, None, []
    method, path = found[0]
    defects = ["multiple route decorators"] if len(found) > 1 else []
    return method, path, defects


def _route_decorator(decorator: ast.expr) -> tuple[str, str] | None:
    if not isinstance(decorator, ast.Call) or not decorator.args:
        return None
    func = decorator.func
    if not isinstance(func, ast.Attribute) or func.attr.lower() not in ROUTE_METHODS:
        return None
    if not isinstance(func.value, ast.Name) or func.value.id not in ROUTE_RECEIVERS:
        return None
    argument = decorator.args[0]
    if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
        return func.attr.upper(), argument.value
    return None


def _python_params(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[dict]:
    positional = list(node.args.posonlyargs) + list(node.args.args)
    pad = len(positional) - len(node.args.defaults)
    defaulted = [False] * pad + [True] * len(node.args.defaults)
    params = []
    for arg, has_default in zip(positional, defaulted):
        if arg.arg in {"self", "cls"}:
            continue
        params.append(_ast_param(arg, required=not has_default))
    for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
        if arg.arg in {"self", "cls"}:
            continue
        params.append(_ast_param(arg, required=default is None))
    return params


def _ast_param(arg: ast.arg, *, required: bool) -> dict:
    return {
        "name": arg.arg,
        "type": _annotation_type(arg.annotation),
        "required": required,
    }


def _annotation_type(annotation: ast.expr | None) -> str:
    if isinstance(annotation, ast.Name):
        return normalize_type(annotation.id)
    return "string"


def _docstring(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    text = ast.get_docstring(node) or ""
    return " ".join(text.split())[:400]


def _javascript_file(path: str, source: str, field: str, notices: list[str]) -> list[dict]:
    raw_handles = len(re.findall(r"ipcMain\.handle\s*\(", source))
    loose_count = len(IPC_LOOSE.findall(source))
    if raw_handles > loose_count:
        notices.append(f"{path} has ipcMain.handle calls outside the supported subset")
    stem = PurePosixPath(path).stem
    strict_at = {match.start() for match in IPC_STRICT.finditer(source)}
    surfaces = []
    seen: dict[str, int] = {}
    for match in IPC_LOOSE.finditer(source):
        channel = match.group("channel")
        seen[channel] = seen.get(channel, 0) + 1
        suffix = "" if seen[channel] == 1 else f"#{seen[channel]}"
        module, handler = _channel_names(channel, stem)
        strict = IPC_STRICT.match(source, match.start())
        defects: list[str] = []
        params: list[dict] = []
        if match.start() not in strict_at or strict is None:
            defects.append("ipc handler signature is outside the supported subset")
        else:
            raw_args = strict.group("args") or ""
            params = [
                {"name": name, "type": "string", "required": True}
                for name in (part.strip() for part in raw_args.split(","))
                if name
            ]
        surfaces.append(
            normalize_surface(
                {
                    "id": f"{path}::{channel}{suffix}",
                    "kind": "ipc",
                    "module": module,
                    "handler": handler,
                    "summary": f"ipc channel {channel}",
                    "params": params,
                    "defects": defects,
                },
                field,
            )
        )
    return surfaces


def _channel_names(channel: str, file_stem: str) -> tuple[str, str]:
    if ":" in channel:
        group, _, rest = channel.partition(":")
        if is_ident(slug(group)) and is_ident(slug(rest)):
            return group, rest
    return file_stem, channel


def _reject_duplicate_ids(surfaces: list[dict]) -> None:
    seen = set()
    for index, surface in enumerate(surfaces):
        if surface["id"] in seen:
            raise CatalogError("duplicate surface id", f"surfaces[{index}].id")
        seen.add(surface["id"])


def _relative_path(value: object, field: str) -> str:
    text = _string(value, field, 160)
    if text.startswith("/") or text.startswith("~") or "\\" in text:
        raise CatalogError("path must be relative", field)
    parts = text.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise CatalogError("path must be relative", field)
    return text


def _optional_method(value: object, field: str) -> str | None:
    if value is None:
        return None
    text = _string(value, field, 16, allow_empty=True).upper()
    return text or None


def _optional_string(value: object, field: str, max_len: int) -> str:
    if value is None:
        return ""
    return _string(value, field, max_len, allow_empty=True)


def _string(value: object, field: str, max_len: int, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise CatalogError("expected a string", field)
    text = value.strip()
    if not allow_empty and not text:
        raise CatalogError("must not be empty", field)
    if len(text) > max_len:
        raise CatalogError("is too long", field)
    return text
