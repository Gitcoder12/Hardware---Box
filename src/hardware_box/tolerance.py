"""Unit-aware linear tolerance stack and clearance-fit calculations."""
from __future__ import annotations

import math
from typing import Any

_TO_MM = {
    "mm": 1.0, "millimeter": 1.0, "millimeters": 1.0,
    "cm": 10.0, "m": 1000.0,
    "um": 0.001, "µm": 0.001, "micron": 0.001, "microns": 0.001,
    "in": 25.4, "inch": 25.4, "inches": 25.4,
    "mil": 0.0254, "mils": 0.0254,
}


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def _unit_factor(unit: str) -> float:
    try:
        return _TO_MM[unit.strip().lower()]
    except (AttributeError, KeyError):
        raise ValueError(f"Unsupported length unit {unit!r}; use mm, cm, m, um, in or mil") from None


def _dimension(item: dict[str, Any], default_unit: str, label: str) -> tuple[float, float, float, float]:
    if not isinstance(item, dict):
        raise ValueError(f"{label} must be an object")
    unit = item.get("unit", default_unit)
    factor = _unit_factor(unit)
    nominal = _number(item.get("nominal"), f"{label}.nominal") * factor
    plus = _number(item.get("tolerance_plus", 0), f"{label}.tolerance_plus") * factor
    minus = _number(item.get("tolerance_minus", 0), f"{label}.tolerance_minus") * factor
    coefficient = _number(item.get("coefficient", 1), f"{label}.coefficient")
    if plus < 0 or minus < 0:
        raise ValueError(f"{label}: tolerances must be non-negative")
    if nominal <= 0:
        raise ValueError(f"{label}.nominal must be greater than zero for a physical size")
    return nominal, plus, minus, coefficient


def analyze_tolerance_stack(dimensions: list[dict[str, Any]], default_unit: str = "mm") -> dict[str, Any]:
    """Analyze an algebraic 1D stack using worst-case and independent RSS methods."""
    if not isinstance(dimensions, list) or not dimensions:
        raise ValueError("dimensions must be a non-empty array")
    _unit_factor(default_unit)
    nominal_total = 0.0
    wc_plus = 0.0
    wc_minus = 0.0
    rss_plus_sq = 0.0
    rss_minus_sq = 0.0
    rows = []
    for index, item in enumerate(dimensions):
        nominal, plus, minus, coefficient = _dimension(item, default_unit, f"dimensions[{index}]")
        nominal_total += coefficient * nominal
        if coefficient >= 0:
            contribution_plus, contribution_minus = coefficient * plus, coefficient * minus
        else:
            contribution_plus, contribution_minus = abs(coefficient) * minus, abs(coefficient) * plus
        wc_plus += contribution_plus
        wc_minus += contribution_minus
        rss_plus_sq += contribution_plus ** 2
        rss_minus_sq += contribution_minus ** 2
        rows.append({
            "name": str(item.get("name", f"Dimension {index + 1}")),
            "nominal_mm": round(nominal, 9),
            "coefficient": coefficient,
            "plus_contribution_mm": round(contribution_plus, 9),
            "minus_contribution_mm": round(contribution_minus, 9),
        })
    rss_plus = math.sqrt(rss_plus_sq)
    rss_minus = math.sqrt(rss_minus_sq)
    return {
        "method": "1D algebraic tolerance stack",
        "input_dimension_count": len(dimensions),
        "unit": "mm",
        "nominal_mm": round(nominal_total, 9),
        "worst_case": {
            "plus_mm": round(wc_plus, 9), "minus_mm": round(wc_minus, 9),
            "minimum_mm": round(nominal_total - wc_minus, 9),
            "maximum_mm": round(nominal_total + wc_plus, 9),
        },
        "rss_independent": {
            "plus_mm": round(rss_plus, 9), "minus_mm": round(rss_minus, 9),
            "minimum_mm": round(nominal_total - rss_minus, 9),
            "maximum_mm": round(nominal_total + rss_plus, 9),
        },
        "contributions": rows,
        "assumptions": [
            "One-dimensional linear stack; rotations, geometric form, datum shift and nonlinear effects are not modeled.",
            "RSS assumes statistically independent contributors; verify distributions and process capability before using it for production decisions.",
            "All values are normalized to millimeters; the source units are interpreted from each input row.",
        ],
    }


def analyze_clearance_fit(hole: dict[str, Any], shaft: dict[str, Any], default_unit: str = "mm") -> dict[str, Any]:
    """Compute limit clearances from hole/shaft size limits."""
    hole_nom, hole_plus, hole_minus, _ = _dimension(hole, default_unit, "hole")
    shaft_nom, shaft_plus, shaft_minus, _ = _dimension(shaft, default_unit, "shaft")
    hole_min, hole_max = hole_nom - hole_minus, hole_nom + hole_plus
    shaft_min, shaft_max = shaft_nom - shaft_minus, shaft_nom + shaft_plus
    min_clearance = hole_min - shaft_max
    max_clearance = hole_max - shaft_min
    if min_clearance >= 0:
        fit = "clearance"
    elif max_clearance < 0:
        fit = "interference"
    else:
        fit = "transition"
    return {
        "fit_type": fit,
        "unit": "mm",
        "hole_limits_mm": {"minimum": round(hole_min, 9), "maximum": round(hole_max, 9)},
        "shaft_limits_mm": {"minimum": round(shaft_min, 9), "maximum": round(shaft_max, 9)},
        "minimum_clearance_mm": round(min_clearance, 9),
        "maximum_clearance_mm": round(max_clearance, 9),
        "assumption": "Ideal size-only cylindrical fit. Does not model form, cylindricity, roughness, temperature, material deformation, coatings, alignment or assembly force.",
    }
