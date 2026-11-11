"""Bill-of-materials helpers for device records."""
from __future__ import annotations

import csv
from pathlib import Path

BOM_COLUMNS = ("reference", "component", "quantity", "manufacturer", "part_number", "specifications")


def bom_rows(record: dict) -> list[dict[str, str | int]]:
    """Convert a validated device record into normalized BOM rows."""
    rows = []
    for index, component in enumerate(record.get("components", []), start=1):
        rows.append({
            "reference": f"ITEM-{index:03d}",
            "component": component["name"],
            "quantity": component["quantity"],
            "manufacturer": component.get("manufacturer", ""),
            "part_number": component.get("part_number", ""),
            "specifications": "; ".join(f"{k}={v}" for k, v in sorted(component.get("specifications", {}).items())),
        })
    return rows


def export_bom_csv(record: dict, destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=BOM_COLUMNS)
        writer.writeheader()
        writer.writerows(bom_rows(record))
    return path
