"""Source extraction subset. Files are parsed, never executed."""

from app.core.catalog import propose
from app.core.errors import CatalogError
from app.core.samples import PYTHON_SAMPLE


def test_python_sample_extracts_functions_and_routes():
    result, inventory = propose(PYTHON_SAMPLE)
    ids = [surface["id"] for surface in inventory["surfaces"]]
    assert "notes.py::_hidden" not in ids
    assert [surface["handler"] for surface in inventory["surfaces"]] == [
        "create_note",
        "search_notes",
        "list_orders",
        "create_order",
    ]
    create = result["grounded"]["commands"][0]
    assert create["executable"] is True
    assert create["argv"] == ["--title", "sample"]
    order = result["grounded"]["commands"][3]
    assert order["kind"] == "http"
    assert order["method"] == "POST"
    assert order["route"] == "/orders"
    assert order["argv"] == ["--sku", "sample"]
    quantity = next(param for param in inventory["surfaces"][3]["params"] if param["name"] == "quantity")
    assert quantity["required"] is False
    assert quantity["type"] == "integer"


def test_class_methods_are_ignored_and_variadic_functions_do_not_bind():
    result, inventory = propose(
        {
            "application": "box-app",
            "files": [
                {
                    "path": "box.py",
                    "source": (
                        "class Box:\n"
                        "    def open_box(self, name):\n"
                        "        return name\n"
                        "\n"
                        "def search(query, *filters):\n"
                        "    return query\n"
                    ),
                }
            ],
        }
    )
    assert [surface["handler"] for surface in inventory["surfaces"]] == ["search"]
    assert result["grounded"]["commands"][0]["executable"] is False
    assert "variadic parameters are not bound" in result["grounded"]["commands"][0]["reasons"]


def test_python_syntax_error_names_the_file():
    try:
        propose({"application": "box-app", "files": [{"path": "box.py", "source": "def (" }]})
    except CatalogError as exc:
        assert exc.field == "files[0].source"
        assert "python syntax error" in exc.message
    else:
        raise AssertionError("expected CatalogError")


def test_relative_path_rejects_parent_segments():
    try:
        propose({"application": "box-app", "files": [{"path": "../box.py", "source": "def ping():\n    return 1\n"}]})
    except CatalogError as exc:
        assert exc.field == "files[0].path"
    else:
        raise AssertionError("expected CatalogError")


def test_ipc_identifier_list_binds_and_destructure_does_not():
    result, _inventory = propose(
        {
            "application": "meetings-app",
            "files": [
                {
                    "path": "main.js",
                    "source": (
                        "ipcMain.handle('meetings:schedule', async (event, title, startsAt) => {});\n"
                        "ipcMain.handle('meetings:broken', async (event, { title }) => {});\n"
                    ),
                }
            ],
        }
    )
    schedule, broken = result["grounded"]["commands"]
    assert schedule["executable"] is True
    assert schedule["path"] == "meetings schedule"
    assert schedule["argv"] == ["--title", "sample", "--starts_at", "sample"]
    assert broken["executable"] is False
    assert "ipc handler signature is outside the supported subset" in broken["reasons"]


def test_javascript_without_handles_is_a_notice():
    result, _inventory = propose(
        {"application": "web-app", "files": [{"path": "view.js", "source": "export const view = 1;\n"}]}
    )
    assert result["grounded"]["proposed"] == 0
    assert result["notices"] == ["view.js contributed no supported surfaces"]
