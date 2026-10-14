"""FastAPI entrypoint. Docker and local commands both use app.main:app."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.errors import CatalogError
from app.core.version import read_version
from app.services.store import Store


def create_app(db_path: str | Path | None = None) -> FastAPI:
    resolved = Path(db_path) if db_path is not None else Path(os.environ.get("PRISM_DB") or "data/prism.sqlite")
    application = FastAPI(title="Prism Console", version=read_version())
    application.state.store = Store(resolved)
    application.add_exception_handler(CatalogError, _catalog_error)
    application.add_exception_handler(RequestValidationError, _invalid_request)
    application.include_router(router, prefix="/api")
    return application


def _catalog_error(_request, exc: CatalogError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": exc.message, "field": exc.field})


def _invalid_request(_request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": "invalid request", "field": ""})


app = create_app()
