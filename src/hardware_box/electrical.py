"""Explainable electrical budget checks for declared design data.

These checks are arithmetic and range checks only. They do not model transients,
thermal effects, PCB trace ampacity, regulation, isolation, EMC, or safety.
"""
from __future__ import annotations
from typing import Any


def analyze_electrical(record: dict[str, Any]) -> dict[str, Any]:
    profile = record.get("electrical", {})
    if not isinstance(profile, dict):
        return {"valid": False, "errors": ["electrical must be an object"], "checks": []}
    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    def check(name: str, status: str, detail: str) -> None:
        checks.append({"name": name, "status": status, "detail": detail})

    supply = profile.get("supply")
    loads = profile.get("loads", [])
    if not profile:
        check("electrical_profile", "unknown", "No electrical profile is declared.")
        return {"valid": True, "known": False, "errors": [], "checks": checks,
                "totals": {"estimated_current_a": None, "estimated_power_w": None},
                "disclaimer": "No electrical profile was supplied; no compatibility claim can be made."}
    if not isinstance(supply, dict):
        errors.append("electrical.supply must be an object")
        supply = {}
    if not isinstance(loads, list):
        errors.append("electrical.loads must be an array")
        loads = []

    voltage = supply.get("voltage_v")
    current_limit = supply.get("current_limit_a")
    voltage_valid = isinstance(voltage, (int, float)) and not isinstance(voltage, bool) and voltage > 0
    if voltage is not None and not voltage_valid:
        errors.append("electrical.supply.voltage_v must be a positive number")
    current_limit_valid = isinstance(current_limit, (int, float)) and not isinstance(current_limit, bool) and current_limit > 0
    if current_limit is not None and not current_limit_valid:
        errors.append("electrical.supply.current_limit_a must be a positive number")

    total_current = 0.0
    complete_current = bool(loads)
    for index, load in enumerate(loads):
        prefix = f"electrical.loads[{index}]"
        if not isinstance(load, dict):
            errors.append(f"{prefix} must be an object")
            complete_current = False
            continue
        name = str(load.get("name", f"load-{index + 1}"))
        qty = load.get("quantity", 1)
        draw = load.get("current_a")
        if type(qty) is not int or qty < 1:
            errors.append(f"{prefix}.quantity must be a positive integer")
            complete_current = False
            continue
        if draw is None:
            complete_current = False
        elif isinstance(draw, bool) or not isinstance(draw, (int, float)) or draw < 0:
            errors.append(f"{prefix}.current_a must be a non-negative number")
            complete_current = False
            continue
        else:
            total_current += float(draw) * qty

        vmin, vmax = load.get("voltage_min_v"), load.get("voltage_max_v")
        if vmin is not None and (isinstance(vmin, bool) or not isinstance(vmin, (int, float)) or vmin < 0):
            errors.append(f"{prefix}.voltage_min_v must be a non-negative number")
        if vmax is not None and (isinstance(vmax, bool) or not isinstance(vmax, (int, float)) or vmax <= 0):
            errors.append(f"{prefix}.voltage_max_v must be a positive number")
        if vmin is not None and vmax is not None and isinstance(vmin, (int, float)) and isinstance(vmax, (int, float)) and vmin > vmax:
            errors.append(f"{prefix}: voltage_min_v exceeds voltage_max_v")
        if voltage_valid and vmin is not None and vmax is not None:
            if all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (vmin, vmax)):
                ok = vmin <= voltage <= vmax
                check(f"{name}_voltage", "pass" if ok else "fail",
                      f"Declared supply {voltage:g} V vs load range {vmin:g}–{vmax:g} V.")
        elif vmin is not None or vmax is not None:
            check(f"{name}_voltage", "unknown", "Supply voltage or complete load voltage range is missing.")

    if voltage is not None and not any(c["name"].endswith("_voltage") for c in checks):
        check("voltage_domain", "unknown", "No complete load voltage ranges were available for comparison.")
    if current_limit_valid:
        if complete_current:
            ok = total_current <= float(current_limit)
            check("current_budget", "pass" if ok else "fail",
                  f"Estimated load current {total_current:.4g} A vs declared limit {float(current_limit):.4g} A.")
        else:
            check("current_budget", "unknown", "At least one load current is missing; total current is incomplete.")
    elif current_limit is not None:
        check("current_budget", "unknown", "Declared current limit is invalid; no budget comparison was performed.")
    else:
        check("current_budget", "unknown", "No supply current limit is declared; overload margin cannot be assessed.")

    known_power = voltage_valid and complete_current
    return {
        "valid": not errors,
        "known": bool(supply and loads),
        "errors": errors,
        "checks": checks,
        "totals": {"estimated_current_a": round(total_current, 6) if complete_current and not errors else None,
                   "estimated_power_w": round(float(voltage) * total_current, 6) if known_power and not errors else None},
        "disclaimer": "Arithmetic screening only. Not a schematic review, electrical safety assessment, thermal analysis, or certification.",
    }
