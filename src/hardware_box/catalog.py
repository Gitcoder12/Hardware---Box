"""SQLite component catalog for reusable, traceable part records."""
from __future__ import annotations
import json, sqlite3
from pathlib import Path
from typing import Any

CATALOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS components (
    mpn TEXT PRIMARY KEY,
    manufacturer TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'other',
    package TEXT,
    description TEXT,
    datasheet_url TEXT,
    lifecycle_status TEXT NOT NULL DEFAULT 'unknown',
    specs_json TEXT NOT NULL DEFAULT '{}',
    provenance_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_components_name ON components(name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_components_manufacturer ON components(manufacturer COLLATE NOCASE);
"""


def _validate(item: dict[str, Any]) -> None:
    for key in ("mpn", "manufacturer", "name"):
        if not isinstance(item.get(key), str) or not item[key].strip():
            raise ValueError(f"{key} must be a non-empty string")
    if item.get("lifecycle_status", "unknown") not in {"active", "nrnd", "obsolete", "unknown"}:
        raise ValueError("lifecycle_status must be active, nrnd, obsolete, or unknown")
    for key in ("specifications", "provenance"):
        if key in item and not isinstance(item[key], dict):
            raise ValueError(f"{key} must be an object")


def _connect(db_path: str | Path):
    p = Path(db_path); p.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(p, timeout=10); db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=10000"); db.executescript(CATALOG_SCHEMA)
    return db


def add_component(db_path: str | Path, item: dict[str, Any]) -> str:
    _validate(item)
    db = _connect(db_path)
    try:
        with db:
            db.execute("""INSERT INTO components(mpn,manufacturer,name,category,package,description,datasheet_url,lifecycle_status,specs_json,provenance_json)
            VALUES(?,?,?,?,?,?,?,?,?,?)""", (item["mpn"], item["manufacturer"], item["name"], item.get("category", "other"),
            item.get("package"), item.get("description"), item.get("datasheet_url"), item.get("lifecycle_status", "unknown"),
            json.dumps(item.get("specifications", {}), sort_keys=True), json.dumps(item.get("provenance", {}), sort_keys=True)))
    finally:
        db.close()
    return item["mpn"]


def get_component(db_path: str | Path, mpn: str) -> dict[str, Any] | None:
    db = _connect(db_path)
    try:
        row = db.execute("SELECT * FROM components WHERE mpn=?", (mpn,)).fetchone()
    finally:
        db.close()
    if row is None: return None
    item = dict(row); item["specifications"] = json.loads(item.pop("specs_json")); item["provenance"] = json.loads(item.pop("provenance_json"))
    return item


def search_components(db_path: str | Path, query: str = "", category: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    if not 1 <= limit <= 1000: raise ValueError("limit must be between 1 and 1000")
    sql = "SELECT * FROM components WHERE 1=1"; args: list[Any] = []
    if query:
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        sql += " AND (mpn LIKE ? ESCAPE '\\' OR name LIKE ? ESCAPE '\\' OR manufacturer LIKE ? ESCAPE '\\')"
        term = f"%{escaped}%"; args.extend([term, term, term])
    if category: sql += " AND category=?"; args.append(category)
    sql += " ORDER BY manufacturer COLLATE NOCASE, name COLLATE NOCASE LIMIT ?"; args.append(limit)
    db = _connect(db_path)
    try:
        rows = db.execute(sql, args).fetchall()
    finally:
        db.close()
    results = []
    for row in rows:
        item = dict(row)
        item["specifications"] = json.loads(item.pop("specs_json"))
        item["provenance"] = json.loads(item.pop("provenance_json"))
        results.append(item)
    return results
