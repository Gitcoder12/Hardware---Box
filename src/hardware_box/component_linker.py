"""Resolve BOM entries against a local component catalog without guessing."""
from __future__ import annotations
from typing import Any
from .catalog import get_component


def link_bom_to_catalog(db_path: str, bom_record: dict[str, Any]) -> dict[str, Any]:
    linked, unresolved = [], []
    for component in bom_record.get("components", []):
        mpn = component.get("part_number") or component.get("mpn")
        catalog_item = get_component(db_path, str(mpn)) if mpn else None
        entry = {"component": component.get("name", component.get("value", "")),
                 "part_number": mpn, "quantity": component.get("quantity", 0)}
        if catalog_item:
            linked.append({**entry, "catalog": catalog_item})
        else:
            unresolved.append({**entry, "reason": "No exact manufacturer part-number match in local catalog."})
    return {"linked_count": len(linked), "unresolved_count": len(unresolved),
            "linked": linked, "unresolved": unresolved,
            "policy": "Exact part-number matching only; no fuzzy substitutions or equivalence claims."}
