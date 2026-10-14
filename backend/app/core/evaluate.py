"""Labeled comparison of the grounded catalog and the thin baseline.

The cases are hand-written inventories, not production traces. A path counts as
a prediction only when that generator marks the command executable. Precision
and recall use executable command paths. When a case has no gold paths and no
predictions, both scores are 1.0 because there was nothing to miss.
"""

import json
import sys

from app.core.catalog import propose
from app.core.samples import SURFACE_SAMPLE

FAILURE_CASES = [
    "A thin lifecycle command with no matching handler is not executable.",
    "The thin generator always uses the group name app, so a handler that lives in another module is a different path.",
    "The thin vocabulary carries no flags, so a matching handler with a required parameter fails binding.",
    "Duplicate command paths and unsupported surface kinds stay out of the executable set.",
    "Module-level Python functions are extracted. Class methods are ignored.",
    "An ipcMain.handle callback with a destructured parameter list is outside the supported subset.",
    "Executable means the argv binds to a declared surface. The target application is not launched.",
]


def evaluation_cases() -> list[dict]:
    return [
        {"name": "lane-desk", "gold": [
            "notes create_note",
            "notes search_notes",
            "meetings schedule_meeting",
            "meetings cancel_meeting",
            "files export_minutes",
            "orders list_orders",
        ], "inventory": SURFACE_SAMPLE},
        {"name": "ledger-defects", "gold": [
            "orders list_orders",
            "orders create_order",
        ], "inventory": {
            "application": "ledger",
            "surfaces": [
                {
                    "id": "orders.list",
                    "kind": "http",
                    "module": "orders",
                    "handler": "listOrders",
                    "method": "GET",
                    "path": "/orders",
                },
                {
                    "id": "orders.create",
                    "kind": "http",
                    "module": "orders",
                    "handler": "createOrder",
                    "method": "POST",
                    "path": "/orders",
                    "params": [{"name": "body", "type": "string", "required": True}],
                },
                {
                    "id": "orders.broken",
                    "kind": "http",
                    "module": "orders",
                    "handler": "createInvoice",
                    "method": "POST",
                },
                {
                    "id": "billing.gui",
                    "kind": "gui",
                    "module": "billing",
                    "handler": "openConsole",
                },
                {
                    "id": "chat.one",
                    "kind": "ipc",
                    "module": "chat",
                    "handler": "sendMessage",
                    "params": [{"name": "text", "type": "string", "required": True}],
                },
                {
                    "id": "chat.two",
                    "kind": "ipc",
                    "module": "chat",
                    "handler": "sendMessage",
                    "params": [{"name": "text", "type": "string", "required": True}],
                },
            ],
        }},
        {"name": "health-service", "gold": ["health status", "app start"], "inventory": {
            "application": "health-service",
            "surfaces": [
                {"id": "health.status", "kind": "function", "module": "health", "handler": "status"},
                {"id": "app.start", "kind": "function", "module": "app", "handler": "start"},
            ],
        }},
        {"name": "gated-start", "gold": ["app start"], "inventory": {
            "application": "gated",
            "surfaces": [
                {
                    "id": "app.start",
                    "kind": "ipc",
                    "module": "app",
                    "handler": "start",
                    "params": [{"name": "config", "type": "string", "required": True}],
                }
            ],
        }},
        {"name": "python-notes", "gold": ["notes create_note", "notes search_notes"], "inventory": {
            "application": "notes-app",
            "files": [
                {
                    "path": "notes.py",
                    "source": (
                        "class Box:\n"
                        "    def open_box(self, name):\n"
                        "        return name\n"
                        "\n"
                        "def create_note(title: str):\n"
                        "    return title\n"
                        "\n"
                        "def search_notes(query: str):\n"
                        "    return query\n"
                    ),
                }
            ],
        }},
        {"name": "ipc-meetings", "gold": ["meetings schedule"], "inventory": {
            "application": "meetings-app",
            "files": [
                {
                    "path": "main.js",
                    "source": (
                        "const { ipcMain } = require('electron');\n"
                        "ipcMain.handle('meetings:schedule', async (event, title, startsAt) => {});\n"
                        "ipcMain.handle('meetings:broken', async (event, { title }) => {});\n"
                    ),
                }
            ],
        }},
    ]


def run_evaluation(cases: list[dict] | None = None) -> dict:
    rows = []
    totals = {
        "grounded": {"true_positives": 0, "predicted": 0, "gold": 0},
        "thin": {"true_positives": 0, "predicted": 0, "gold": 0},
    }
    for case in cases or evaluation_cases():
        result, _inventory = propose(case["inventory"])
        gold = set(case["gold"])
        row = {"name": case["name"], "gold": sorted(gold)}
        for generator in ("grounded", "thin"):
            predicted = {
                command["path"]
                for command in result[generator]["commands"]
                if command["executable"]
            }
            scored = _score(predicted, gold)
            row[generator] = scored
            bucket = totals[generator]
            bucket["true_positives"] += scored["true_positives"]
            bucket["predicted"] += len(predicted)
            bucket["gold"] += len(gold)
        rows.append(row)
    return {
        "case_count": len(rows),
        "convention": (
            "A command path is predicted only when that generator marks it executable. "
            "A case with no gold paths and no predictions scores 1.0."
        ),
        "grounded": _with_rates(totals["grounded"]),
        "thin": _with_rates(totals["thin"]),
        "cases": rows,
        "failure_cases": list(FAILURE_CASES),
    }


def _score(predicted: set[str], gold: set[str]) -> dict:
    true_positives = len(predicted & gold)
    rates = _rates(true_positives, len(predicted), len(gold))
    return {
        "predicted": sorted(predicted),
        "false_positives": sorted(predicted - gold),
        "false_negatives": sorted(gold - predicted),
        "true_positives": true_positives,
        **rates,
    }


def _with_rates(bucket: dict) -> dict:
    rates = _rates(bucket["true_positives"], bucket["predicted"], bucket["gold"])
    return {**bucket, **rates}


def _rates(true_positives: int, predicted: int, gold: int) -> dict:
    if predicted == 0 and gold == 0:
        precision = recall = f1 = 1.0
    else:
        precision = true_positives / predicted if predicted else 0.0
        recall = true_positives / gold if gold else 0.0
        f1 = 0.0 if precision + recall == 0 else (2 * precision * recall / (precision + recall))
    return {
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(f1, 6),
    }


def main() -> None:
    json.dump(run_evaluation(), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
