"""SQLite storage for analyses and the audit log."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY,
    application TEXT NOT NULL,
    created_at TEXT NOT NULL,
    inventory_json TEXT NOT NULL,
    result_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    analysis_id INTEGER REFERENCES analyses(id),
    action TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        try:
            connection.executescript(SCHEMA)
            connection.commit()
        finally:
            connection.close()

    def create_analysis(self, result: dict, inventory: dict) -> dict:
        created_at = _now()
        grounded = result["grounded"]
        detail = (
            f"{result['application']} proposed={grounded['proposed']} "
            f"executable={grounded['executable']}"
        )
        with self._session() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                cursor = connection.execute(
                    """
                    INSERT INTO analyses (application, created_at, inventory_json, result_json)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        result["application"],
                        created_at,
                        json.dumps(inventory, sort_keys=True),
                        json.dumps(result, sort_keys=True),
                    ),
                )
                analysis_id = int(cursor.lastrowid)
                connection.execute(
                    """
                    INSERT INTO audit_log (analysis_id, action, detail, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (analysis_id, "analysis.created", detail, created_at),
                )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
        record = self.get_analysis(analysis_id)
        if record is None:
            raise RuntimeError("analysis insert was not readable")
        return record

    def get_analysis(self, analysis_id: int) -> dict | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT id, application, created_at, inventory_json, result_json FROM analyses WHERE id = ?",
                (analysis_id,),
            ).fetchone()
        if row is None:
            return None
        return _record(row)

    def list_analyses(self, application: str, limit: int, offset: int) -> tuple[list[dict], int]:
        where = ""
        params: list[object] = []
        if application:
            where = "WHERE application LIKE ? ESCAPE '\\'"
            params.append(_like(application))
        with self._session() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) AS n FROM analyses {where}",
                params,
            ).fetchone()["n"]
            rows = connection.execute(
                f"""
                SELECT id, application, created_at, inventory_json, result_json
                FROM analyses {where}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
        return [_record(row) for row in rows], int(total)

    def record_export(self, analysis_id: int, application: str) -> None:
        with self._session() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    """
                    INSERT INTO audit_log (analysis_id, action, detail, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (analysis_id, "analysis.exported", application, _now()),
                )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise

    def list_audit(self, limit: int, offset: int) -> tuple[list[dict], int]:
        with self._session() as connection:
            total = connection.execute("SELECT COUNT(*) AS n FROM audit_log").fetchone()["n"]
            rows = connection.execute(
                """
                SELECT id, analysis_id, action, detail, created_at
                FROM audit_log
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        items = [
            {
                "id": row["id"],
                "analysis_id": row["analysis_id"],
                "action": row["action"],
                "detail": row["detail"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
        return items, int(total)

    @contextmanager
    def _session(self):
        connection = sqlite3.connect(self.path, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
        finally:
            connection.close()


def _record(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "application": row["application"],
        "created_at": row["created_at"],
        "inventory": json.loads(row["inventory_json"]),
        "result": json.loads(row["result_json"]),
    }


def _like(fragment: str) -> str:
    escaped = fragment.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
