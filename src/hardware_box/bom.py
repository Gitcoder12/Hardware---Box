"""Bill-of-materials helpers for device records."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

BOM_COLUMNS = ("reference", "component", "quantity", "manufacturer", "part_number", "specifications")


def bom_rows(record: dict[str, Any]) -> list[dict[str, str | int]]:
    """Convert a device record into normalized BOM rows with strict validation."""
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    components = record.get("components")
    if not isinstance(components, list):
        raise ValueError("record must contain a components list")

    rows: list[dict[str, str | int]] = []
    for index, component in enumerate(components, start=1):
        label = f"components[{index - 1}]"
        if not isinstance(component, dict):
            raise ValueError(f"{label} must be an object")
        name = component.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{label}.name is required and must be non-empty")
        quantity = component.get("quantity")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            raise ValueError(f"{label}.quantity must be a positive integer")
        specifications = component.get("specifications", {})
        if not isinstance(specifications, dict):
            raise ValueError(f"{label}.specifications must be an object")
        rows.append({
            "reference": f"ITEM-{index:03d}",
            "component": name.strip(),
            "quantity": quantity,
            "manufacturer": str(component.get("manufacturer", "")),
            "part_number": str(component.get("part_number", "")),
            "specifications": "; ".join(
                f"{key}={value}" for key, value in sorted(specifications.items())
            ),
        })
    return rows


def export_bom_csv(record: dict[str, Any], destination: str | Path) -> Path:
    """Validate and export a device BOM as UTF-8-with-BOM CSV."""
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = bom_rows(record)
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=BOM_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path
