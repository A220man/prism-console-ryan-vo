"""Score a grounded command catalog and a thin lifecycle baseline.

Executable means the command names one well-formed surface and a dry-run argv
binds every required parameter. It does not mean the target application was
launched.
"""

import re

from app.core.errors import CatalogError
from app.core.extract import assemble_inventory
from app.core.naming import is_ident, placeholder, slug

THIN_VERBS = ("start", "stop", "status", "chat", "meeting")
ALLOWED_KINDS = {"ipc", "http", "function"}
ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
PATH_PARAM = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def propose(payload: object) -> tuple[dict, dict]:
    """Return the scored catalog and the assembled inventory."""
    inventory = assemble_inventory(payload)
    result = {
        "application": inventory["application"],
        "executable_name": inventory["executable_name"],
        "surface_count": len(inventory["surfaces"]),
        "notices": list(inventory["notices"]),
        "grounded": _metrics(_grounded_commands(inventory), inventory["surfaces"]),
        "thin": _metrics(_thin_commands(inventory), inventory["surfaces"]),
    }
    stored = {
        "application": inventory["application"],
        "executable_name": inventory["executable_name"],
        "surfaces": inventory["surfaces"],
    }
    return result, stored


def bind_argv(params: list[dict], argv: list[object]) -> tuple[dict, list[str]]:
    """Bind flag/value pairs. Returns the bound map and zero or more reasons."""
    known = {param["flag"]: param for param in params}
    bound: dict[str, str] = {}
    reasons: list[str] = []
    seen: set[str] = set()
    index = 0
    while index < len(argv):
        token = argv[index]
        if not isinstance(token, str) or not token.startswith("--") or len(token) < 3:
            reasons.append("expected a flag")
            break
        flag = token[2:]
        if flag not in known:
            reasons.append(f"unknown flag: {flag}")
            index += 2 if index + 1 < len(argv) else 1
            continue
        if index + 1 >= len(argv) or not isinstance(argv[index + 1], str):
            reasons.append(f"missing value for --{flag}")
            break
        if flag in seen:
            reasons.append(f"duplicate flag: {flag}")
        seen.add(flag)
        bound[known[flag]["name"]] = argv[index + 1]
        index += 2
    for param in params:
        if param["required"] and param["name"] not in bound:
            reasons.append(f"required parameter missing: {param['name']}")
    return bound, reasons


def _grounded_commands(inventory: dict) -> list[dict]:
    commands = [
        _score_surface(
            inventory["executable_name"],
            surface,
            group=slug(surface["module"]) if surface["module"] else "",
            verb=slug(surface["handler"]) if surface["handler"] else "",
            argv=_suggested_argv(surface),
            check_names=True,
        )
        for surface in inventory["surfaces"]
    ]
    _fail_duplicate_paths(commands)
    return commands


def _thin_commands(inventory: dict) -> list[dict]:
    by_verb: dict[str, list[dict]] = {}
    for surface in inventory["surfaces"]:
        verb = slug(surface["handler"]) if surface["handler"] else ""
        by_verb.setdefault(verb, []).append(surface)
    commands = []
    for verb in THIN_VERBS:
        matches = by_verb.get(verb, [])
        if len(matches) == 1:
            command = _score_surface(
                inventory["executable_name"],
                matches[0],
                group="app",
                verb=verb,
                argv=[],
                check_names=False,
            )
        elif not matches:
            command = _unbound_thin(inventory["executable_name"], verb, "no source surface bound")
        else:
            ids = ", ".join(surface["id"] for surface in matches)
            command = _unbound_thin(
                inventory["executable_name"],
                verb,
                f"verb matches multiple surfaces: {ids}",
            )
        commands.append(command)
    return commands


def _score_surface(
    executable_name: str,
    surface: dict,
    *,
    group: str,
    verb: str,
    argv: list[str],
    check_names: bool,
) -> dict:
    reasons = list(surface.get("defects") or [])
    if check_names and not is_ident(group):
        reasons.append("module is not a command name")
    if check_names and not is_ident(verb):
        reasons.append("handler is not a command name")
    if surface["kind"] not in ALLOWED_KINDS:
        reasons.append("unsupported surface kind")
    if surface["kind"] == "http":
        reasons.extend(_http_reasons(surface))
    flags = [param["flag"] for param in surface["params"]]
    bound: dict[str, str] = {}
    if any(not is_ident(flag) for flag in flags):
        reasons.append("parameter name is not a flag name")
    elif len(set(flags)) != len(flags):
        reasons.append("duplicate flag")
    else:
        bound, bind_reasons = bind_argv(surface["params"], argv)
        reasons.extend(bind_reasons)
    path = f"{group} {verb}" if is_ident(group) and is_ident(verb) else ""
    if not bound and reasons:
        bound = {}
    return _command(
        executable_name=executable_name,
        surface=surface,
        path=path,
        group=group,
        verb=verb,
        argv=argv,
        reasons=reasons,
        bound=bound if not reasons else {},
        surface_id=surface["id"],
    )


def _http_reasons(surface: dict) -> list[str]:
    reasons = []
    method = surface.get("method") or ""
    route = surface.get("path") or ""
    if method not in ALLOWED_METHODS:
        reasons.append("http method is missing or unsupported")
    if not route.startswith("/"):
        reasons.append("http path must start with /")
    else:
        reasons.extend(_path_param_reasons(route, surface["params"]))
    return reasons


def _path_param_reasons(route: str, params: list[dict]) -> list[str]:
    if route.count("{") != route.count("}"):
        return ["malformed path parameter"]
    names = PATH_PARAM.findall(route)
    if route.count("{") != len(names):
        return ["malformed path parameter"]
    declared = {param["name"] for param in params} | {param["flag"] for param in params}
    return [f"path parameter not declared: {name}" for name in names if name not in declared]


def _suggested_argv(surface: dict) -> list[str]:
    argv = []
    for param in surface["params"]:
        if param["required"] and is_ident(param["flag"]):
            argv.extend([f"--{param['flag']}", placeholder(param["type"])])
    return argv


def _fail_duplicate_paths(commands: list[dict]) -> None:
    groups: dict[str, list[dict]] = {}
    for command in commands:
        if command["path"]:
            groups.setdefault(command["path"], []).append(command)
    for grouped in groups.values():
        if len(grouped) < 2:
            continue
        for command in grouped:
            if "duplicate command path" not in command["reasons"]:
                command["reasons"].append("duplicate command path")
            command["executable"] = False
            command["bound"] = {}


def _unbound_thin(executable_name: str, verb: str, reason: str) -> dict:
    return _command(
        executable_name=executable_name,
        surface=None,
        path=f"app {verb}",
        group="app",
        verb=verb,
        argv=[],
        reasons=[reason],
        bound={},
        surface_id=None,
    )


def _command(
    *,
    executable_name: str,
    surface: dict | None,
    path: str,
    group: str,
    verb: str,
    argv: list[str],
    reasons: list[str],
    bound: dict,
    surface_id: str | None,
) -> dict:
    parts = [executable_name]
    if path:
        parts.extend(path.split(" "))
    parts.extend(argv)
    return {
        "path": path,
        "surface_id": surface_id,
        "group": group,
        "verb": verb,
        "handler": surface["handler"] if surface else "",
        "kind": surface["kind"] if surface else "",
        "summary": surface["summary"] if surface else "",
        "method": surface["method"] if surface else None,
        "route": surface["path"] if surface else None,
        "executable": not reasons,
        "reasons": reasons,
        "argv": list(argv),
        "invocation": " ".join(parts),
        "bound": bound,
    }


def _metrics(commands: list[dict], surfaces: list[dict]) -> dict:
    executable = [command for command in commands if command["executable"]]
    covered = {command["surface_id"] for command in executable if command["surface_id"]}
    proposed = len(commands)
    surface_count = len(surfaces)
    return {
        "proposed": proposed,
        "executable": len(executable),
        "surfaces_covered": len(covered),
        "coverage": _ratio(len(covered), surface_count),
        "correctness": _ratio(len(executable), proposed),
        "commands": commands,
    }


def _ratio(part: int, whole: int) -> float:
    if whole == 0:
        return 0.0
    return round(part / whole, 6)


def require_page(limit: int, offset: int) -> tuple[int, int]:
    if limit < 1 or limit > 100:
        raise CatalogError("limit must be from 1 to 100", "limit")
    if offset < 0:
        raise CatalogError("offset must be zero or greater", "offset")
    return limit, offset
