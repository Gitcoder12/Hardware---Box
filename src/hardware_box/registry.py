"""SQLite-backed local hardware registry."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .validation import validate_device

SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    manufacturer TEXT NOT NULL,
    revision TEXT NOT NULL,
    verification TEXT NOT NULL,
    record_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_devices_category ON devices(category);
CREATE INDEX IF NOT EXISTS idx_devices_name ON devices(name COLLATE NOCASE);
"""


@contextmanager
def connect(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    """Open a database connection and always close it after the transaction."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=10000")
    db.executescript(SCHEMA)
    try:
        with db:
            yield db
    finally:
        db.close()


def _validated(record: dict) -> None:
    errors = validate_device(record)
    if errors:
        raise ValueError("; ".join(errors))


def add_device(db_path: str | Path, record: dict) -> str:
    _validated(record)
    with connect(db_path) as db:
        db.execute(
            "INSERT INTO devices(id,name,category,manufacturer,revision,verification,record_json) VALUES(?,?,?,?,?,?,?)",
            (record["id"], record["name"], record["category"], record["manufacturer"],
             record["revision"], record["provenance"]["verification"],
             json.dumps(record, sort_keys=True, ensure_ascii=False)),
        )
    return record["id"]


def update_device(db_path: str | Path, record: dict) -> None:
    _validated(record)
    with connect(db_path) as db:
        cur = db.execute(
            "UPDATE devices SET name=?,category=?,manufacturer=?,revision=?,verification=?,record_json=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (record["name"], record["category"], record["manufacturer"], record["revision"],
             record["provenance"]["verification"], json.dumps(record, sort_keys=True, ensure_ascii=False),
             record["id"]),
        )
        if cur.rowcount == 0:
            raise KeyError(record["id"])


def get_device(db_path: str | Path, device_id: str) -> dict | None:
    with connect(db_path) as db:
        row = db.execute("SELECT record_json FROM devices WHERE id=?", (device_id,)).fetchone()
    return json.loads(row["record_json"]) if row else None


def list_devices(db_path: str | Path, category: str | None = None, query: str | None = None) -> list[dict]:
    sql = "SELECT record_json FROM devices WHERE 1=1"
    params: list[str] = []
    if category:
        sql += " AND category=?"
        params.append(category)
    if query:
        # Escape LIKE metacharacters so search terms are treated literally.
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        sql += " AND (name LIKE ? ESCAPE '\\' OR manufacturer LIKE ? ESCAPE '\\' OR id LIKE ? ESCAPE '\\')"
        term = f"%{escaped}%"
        params.extend([term, term, term])
    sql += " ORDER BY name COLLATE NOCASE, id"
    with connect(db_path) as db:
        rows = db.execute(sql, params).fetchall()
    return [json.loads(row["record_json"]) for row in rows]


def delete_device(db_path: str | Path, device_id: str) -> bool:
    with connect(db_path) as db:
        cur = db.execute("DELETE FROM devices WHERE id=?", (device_id,))
    return cur.rowcount > 0
