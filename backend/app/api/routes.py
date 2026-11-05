"""Catalog, history, evaluation, and replay routes."""

from typing import Any

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from app.core.catalog import bind_argv, propose, require_page
from app.core.errors import CatalogError
from app.core.evaluate import run_evaluation
from app.core.samples import PYTHON_SAMPLE, SURFACE_SAMPLE
from app.core.version import read_version
from app.models.schemas import analysis_response, audit_response, export_payload

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": read_version()}


@router.get("/sample")
def sample(kind: str = "surfaces") -> dict:
    if kind == "surfaces":
        return SURFACE_SAMPLE
    if kind == "python":
        return PYTHON_SAMPLE
    raise CatalogError("sample kind must be surfaces or python", "kind")


@router.get("/evaluation")
def evaluation() -> dict:
    return run_evaluation()


@router.post("/analyses")
def create_analysis(request: Request, payload: Any = Body(...)) -> dict:
    result, inventory = propose(payload)
    record = request.app.state.store.create_analysis(result, inventory)
    return analysis_response(record, include_commands=True)


@router.get("/analyses")
def list_analyses(
    request: Request,
    application: str = "",
    limit: int = 20,
    offset: int = 0,
) -> dict:
    limit, offset = require_page(limit, offset)
    records, total = request.app.state.store.list_analyses(application.strip(), limit, offset)
    return {
        "items": [analysis_response(record, include_commands=False) for record in records],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/analyses/{analysis_id}", response_model=None)
def get_analysis(request: Request, analysis_id: int) -> dict | JSONResponse:
    record = request.app.state.store.get_analysis(analysis_id)
    if record is None:
        return _missing()
    return analysis_response(record, include_commands=True)


@router.get("/analyses/{analysis_id}/export", response_model=None)
def export_analysis(request: Request, analysis_id: int) -> dict | JSONResponse:
    record = request.app.state.store.get_analysis(analysis_id)
    if record is None:
        return _missing()
    request.app.state.store.record_export(analysis_id, record["application"])
    return export_payload(record)


@router.post("/analyses/{analysis_id}/replay", response_model=None)
def replay_argv(
    request: Request,
    analysis_id: int,
    argv: list[str] = Body(...),
    command_path: str = Body(...),
    generator: str = Body("grounded"),
) -> dict | JSONResponse:
    """Replay a user-supplied argv against a saved command."""
    record = request.app.state.store.get_analysis(analysis_id)
    if record is None:
        return _missing()

    result = record["result"]
    generator_name = "grounded" if generator == "grounded" else "thin"
    generator_data = result.get(generator_name, {})
    commands = generator_data.get("commands", [])

    # Get the inventory to look up surface params
    inventory = record["inventory"]
    surfaces_by_id = {s["id"]: s for s in inventory.get("surfaces", [])}

    for command in commands:
        if command["path"] == command_path:
            # Get params from the surface
            surface_id = command.get("surface_id")
            if surface_id and surface_id in surfaces_by_id:
                params = surfaces_by_id[surface_id].get("params", [])
            else:
                # For commands without surface_id, no params available
                params = []
            bound, reasons = bind_argv(params, argv)
            return {
                "command_path": command_path,
                "generator": generator_name,
                "bound": bound,
                "reasons": reasons,
                "success": len(reasons) == 0,
            }
    return JSONResponse(status_code=404, content={"error": "command not found", "field": "command_path"})

@router.get("/audit")
def list_audit(request: Request, limit: int = 20, offset: int = 0) -> dict:
    limit, offset = require_page(limit, offset)
    items, total = request.app.state.store.list_audit(limit, offset)
    return audit_response(items, total, limit, offset)


def _missing() -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": "analysis not found", "field": "id"})
