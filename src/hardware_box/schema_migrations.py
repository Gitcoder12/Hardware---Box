"""Versioned device-record migrations. Migrations are deterministic and non-destructive."""
from __future__ import annotations
from copy import deepcopy
from typing import Any

CURRENT_SCHEMA_VERSION = 1


def migrate_record(record: dict[str, Any], target_version: int = CURRENT_SCHEMA_VERSION) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise TypeError("record must be a JSON object")
    if target_version != CURRENT_SCHEMA_VERSION:
        raise ValueError(f"Only target schema version {CURRENT_SCHEMA_VERSION} is supported")
    result = deepcopy(record)
    version = result.get("schema_version", 0)
    if type(version) is not int or version < 0:
        raise ValueError("schema_version must be a non-negative integer")
    if version > CURRENT_SCHEMA_VERSION:
        raise ValueError(f"Record schema version {version} is newer than supported version {CURRENT_SCHEMA_VERSION}")
    if version == 0:
        # v0 records are the original pre-versioned Hardware-Box record shape.
        result["schema_version"] = 1
    return result
