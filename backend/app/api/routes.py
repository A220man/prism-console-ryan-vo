"""Catalog, history, evaluation, and replay routes."""
import json

from typing import Any

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from app.core.catalog import bind_argv, propose, require_page
from app.core.errors import CatalogError
from app.core.evaluate import run_evaluation, _score
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

@router.post("/analyses/{analysis_id}/score", response_model=None)
def score_agent_commands_endpoint(
    request: Request,
    payload: dict = Body(...),
) -> dict | JSONResponse:
    """Score agent-pasted commands against the grounded catalog."""
    from app.core.evaluate import _score
    
    analysis_id = payload.get("analysis_id")
    if not analysis_id:
        return JSONResponse(
            status_code=400,
            content={"error": "missing analysis_id", "field": "analysis_id"},
        )
    
    store: Store = request.app.state.store
    analysis = store.get_analysis(analysis_id)
    if analysis is None:
        return JSONResponse(
            status_code=404,
            content={"error": "analysis not found", "field": "id"},
        )
    
    # Use the grounded commands from the analysis result
    # analysis has result_json stored which contains grounded commands
    grounded_commands = analysis.get("result", {}).get("grounded", {}).get("commands", [])
    grounded_paths = {
        cmd["path"] for cmd in grounded_commands if cmd.get("executable")
    }
    
    # Extract pasted command paths from payload
    pasted_commands = set(payload.get("commands", []))
    
    # Compute scores
    scores = _score(pasted_commands, grounded_paths)
    
    # Compute false negatives: grounded paths not in pasted commands
    false_negatives = list(grounded_paths - pasted_commands)
    
    return JSONResponse(
        status_code=200,
        content={
            "precision": scores["precision"],
            "recall": scores["recall"],
            "true_positives": scores["true_positives"],
            "false_positives": scores["false_positives"],
            "false_negatives": false_negatives,
            "predicted": scores["predicted"],
            "gold": len(grounded_commands),
        },
    )


@router.get("/audit")
def list_audit(request: Request, limit: int = 20, offset: int = 0) -> dict:
    limit, offset = require_page(limit, offset)
    items, total = request.app.state.store.list_audit(limit, offset)
    return audit_response(items, total, limit, offset)


def _missing() -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": "analysis not found", "field": "id"})
