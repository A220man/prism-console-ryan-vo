"""Shape stored records into the public response envelope."""

_GENERATOR_FIELDS = (
    "proposed",
    "executable",
    "surfaces_covered",
    "coverage",
    "correctness",
)


def analysis_response(record: dict, *, include_commands: bool) -> dict:
    result = record["result"]
    return {
        "id": record["id"],
        "application": result["application"],
        "executable_name": result["executable_name"],
        "created_at": record["created_at"],
        "surface_count": result["surface_count"],
        "notices": list(result.get("notices") or []),
        "grounded": _generator(result["grounded"], include_commands=include_commands),
        "thin": _generator(result["thin"], include_commands=include_commands),
    }


def export_payload(record: dict) -> dict:
    result = record["result"]
    return {
        "application": result["application"],
        "executable_name": result["executable_name"],
        "commands": result["grounded"]["commands"],
    }


def audit_response(items: list[dict], total: int, limit: int, offset: int) -> dict:
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def _generator(block: dict, *, include_commands: bool) -> dict:
    shaped = {field: block[field] for field in _GENERATOR_FIELDS}
    if include_commands:
        shaped["commands"] = block["commands"]
    return shaped
