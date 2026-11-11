"""Conservative interface compatibility analysis with structured evidence."""
from __future__ import annotations
from typing import Any


def _interface_map(device: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for item in device.get("interfaces", []) if isinstance(device.get("interfaces", []), list) else []:
        if isinstance(item, str):
            result[item.casefold()] = {"name": item, "detail_level": "label_only"}
        elif isinstance(item, dict) and isinstance(item.get("name"), str):
            result[item["name"].casefold()] = dict(item, detail_level="structured")
    return result


def compare_devices(left: dict, right: dict) -> dict:
    li, ri = _interface_map(left), _interface_map(right)
    shared = sorted(li.keys() & ri.keys())
    only_left, only_right = sorted(li.keys() - ri.keys()), sorted(ri.keys() - li.keys())
    details = []
    for key in shared:
        a, b = li[key], ri[key]
        issues, unknown = [], []
        for field in ("protocol", "connector", "pin_count"):
            av, bv = a.get(field), b.get(field)
            if av is not None and bv is not None and str(av).casefold() != str(bv).casefold():
                issues.append(f"{field} mismatch: {av!r} vs {bv!r}")
            elif av is None or bv is None:
                unknown.append(f"{field} not declared on both sides")
        da, db = a.get("direction"), b.get("direction")
        endpoint_directions = {"input", "output", "power_in", "power_out"}
        if isinstance(da, str) and isinstance(db, str) and da in endpoint_directions and db in endpoint_directions and da == db:
            issues.append(f"direction conflict: both interfaces are declared {da}")
        elif da is None or db is None:
            unknown.append("direction not declared on both sides")
        for low, high, label in (("voltage_min_v", "voltage_max_v", "voltage range"),):
            a_lo, a_hi, b_lo, b_hi = a.get(low), a.get(high), b.get(low), b.get(high)
            if all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (a_lo, a_hi, b_lo, b_hi)):
                if max(a_lo, b_lo) > min(a_hi, b_hi):
                    issues.append(f"{label} does not overlap")
            else:
                unknown.append(f"{label} not fully declared")
        status = "incompatible" if issues else ("unknown" if unknown else "potentially_compatible")
        details.append({"interface": key, "status": status, "issues": issues, "unknowns": unknown})
    same_category = left.get("category") == right.get("category")
    overlap = round(len(shared) / len(li.keys() | ri.keys()), 3) if li or ri else 1.0
    if any(d["status"] == "incompatible" for d in details):
        assessment = "declared_conflict"
    elif shared:
        # Preserve the original meaning: a shared label is only a potential overlap,
        # never a positive compatibility decision.
        assessment = "potential_overlap"
    else:
        assessment = "insufficient_evidence"
    return {
        "same_category": same_category,
        "shared_interfaces": shared,
        "only_left": only_left,
        "only_right": only_right,
        "interface_overlap": overlap,
        "interface_details": details,
        "assessment": assessment,
        "warning": "Name overlap is not proof of compatibility. Checks use only declared metadata and do not establish pinout, timing, signal integrity, firmware, mechanical fit, or safety.",
    }
