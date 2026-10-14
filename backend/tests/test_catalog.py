"""Catalog scoring: coverage, binding, and the thin baseline."""

from app.core.catalog import bind_argv, propose
from app.core.errors import CatalogError
from app.core.samples import SURFACE_SAMPLE


def _paths(result, generator="grounded", *, executable_only=True):
    commands = result[generator]["commands"]
    if executable_only:
        commands = [command for command in commands if command["executable"]]
    return [command["path"] for command in commands]


def test_grounded_catalog_covers_declared_surfaces():
    result, _inventory = propose(SURFACE_SAMPLE)
    assert result["surface_count"] == 6
    assert _paths(result) == [
        "notes create_note",
        "notes search_notes",
        "meetings schedule_meeting",
        "meetings cancel_meeting",
        "files export_minutes",
        "orders list_orders",
    ]
    assert result["grounded"]["coverage"] == 1
    assert result["grounded"]["correctness"] == 1


def test_required_flags_bind_and_optional_flags_are_omitted():
    result, _inventory = propose(SURFACE_SAMPLE)
    create = result["grounded"]["commands"][0]
    assert create["argv"] == ["--title", "sample"]
    assert create["bound"] == {"title": "sample"}
    assert "--body" not in create["invocation"]


def test_http_list_uses_integer_placeholder_from_annotation_equivalent_type():
    result, _inventory = propose(
        {
            "application": "ledger",
            "surfaces": [
                {
                    "id": "orders.create",
                    "kind": "http",
                    "module": "orders",
                    "handler": "createOrder",
                    "method": "post",
                    "path": "/orders/{order_id}",
                    "params": [
                        {"name": "order_id", "type": "int", "required": True},
                        {"name": "note", "type": "string", "required": False},
                    ],
                }
            ],
        }
    )
    command = result["grounded"]["commands"][0]
    assert command["executable"] is True
    assert command["method"] == "POST"
    assert command["argv"] == ["--order_id", "1"]


def test_thin_baseline_does_not_cover_domain_commands():
    result, _inventory = propose(SURFACE_SAMPLE)
    assert result["thin"]["proposed"] == 5
    assert result["thin"]["executable"] == 0
    assert result["thin"]["coverage"] == 0
    assert _paths(result, "thin", executable_only=False) == [
        "app start",
        "app stop",
        "app status",
        "app chat",
        "app meeting",
    ]


def test_thin_match_without_required_params_is_executable_under_app_group():
    result, _inventory = propose(
        {
            "application": "health-service",
            "surfaces": [
                {"id": "health.status", "kind": "function", "module": "health", "handler": "status"}
            ],
        }
    )
    status = next(command for command in result["thin"]["commands"] if command["verb"] == "status")
    assert status["executable"] is True
    assert status["path"] == "app status"
    assert result["grounded"]["commands"][0]["path"] == "health status"


def test_thin_match_fails_when_required_parameter_is_absent():
    result, _inventory = propose(
        {
            "application": "gated",
            "surfaces": [
                {
                    "id": "app.start",
                    "kind": "ipc",
                    "module": "app",
                    "handler": "start",
                    "params": [{"name": "config", "required": True}],
                }
            ],
        }
    )
    start = result["thin"]["commands"][0]
    assert start["executable"] is False
    assert "required parameter missing: config" in start["reasons"]
    assert result["grounded"]["commands"][0]["executable"] is True


def test_duplicate_command_paths_are_not_executable():
    result, _inventory = propose(
        {
            "application": "chat-app",
            "surfaces": [
                {"id": "chat.one", "kind": "ipc", "module": "chat", "handler": "sendMessage", "params": [{"name": "text"}]},
                {"id": "chat.two", "kind": "ipc", "module": "chat", "handler": "sendMessage", "params": [{"name": "text"}]},
            ],
        }
    )
    assert result["grounded"]["executable"] == 0
    assert all("duplicate command path" in command["reasons"] for command in result["grounded"]["commands"])


def test_http_without_path_and_unknown_kind_fail_closed():
    result, _inventory = propose(
        {
            "application": "ledger",
            "surfaces": [
                {"id": "orders.broken", "kind": "http", "module": "orders", "handler": "createInvoice", "method": "POST"},
                {"id": "billing.gui", "kind": "gui", "module": "billing", "handler": "openConsole"},
            ],
        }
    )
    broken, gui = result["grounded"]["commands"]
    assert broken["executable"] is False
    assert "http path must start with /" in broken["reasons"]
    assert gui["executable"] is False
    assert "unsupported surface kind" in gui["reasons"]


def test_missing_path_parameter_is_not_executable():
    result, _inventory = propose(
        {
            "application": "ledger",
            "surfaces": [
                {
                    "id": "orders.get",
                    "kind": "http",
                    "module": "orders",
                    "handler": "getOrder",
                    "method": "GET",
                    "path": "/orders/{order_id}",
                    "params": [],
                }
            ],
        }
    )
    command = result["grounded"]["commands"][0]
    assert command["executable"] is False
    assert "path parameter not declared: order_id" in command["reasons"]


def test_empty_inventory_has_zero_coverage():
    result, _inventory = propose({"application": "empty-app", "surfaces": []})
    assert result["grounded"]["proposed"] == 0
    assert result["grounded"]["coverage"] == 0
    assert result["grounded"]["correctness"] == 0
    assert result["thin"]["executable"] == 0


def test_malformed_inventory_is_rejected():
    try:
        propose({"application": "???", "surfaces": []})
    except CatalogError as exc:
        assert exc.field == "application"
    else:
        raise AssertionError("expected CatalogError")


def test_duplicate_surface_id_is_rejected():
    surface = {"id": "notes.create", "kind": "function", "module": "notes", "handler": "create"}
    try:
        propose({"application": "notes", "surfaces": [surface, dict(surface)]})
    except CatalogError as exc:
        assert exc.field == "surfaces[1].id"
    else:
        raise AssertionError("expected CatalogError")


def test_bind_argv_rejects_unknown_and_missing_flags():
    params = [{"name": "title", "flag": "title", "required": True, "type": "string"}]
    bound, reasons = bind_argv(params, ["--title", "weekly"])
    assert bound == {"title": "weekly"}
    assert reasons == []
    _bound, missing = bind_argv(params, [])
    assert "required parameter missing: title" in missing
    _bound, unknown = bind_argv(params, ["--title", "weekly", "--extra", "1"])
    assert "unknown flag: extra" in unknown
