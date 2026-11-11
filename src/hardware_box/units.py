"""Small, explicit unit conversion helpers used by engineering checks.

Values are never inferred from a bare number: callers must supply a unit.
"""
from __future__ import annotations

_FACTORS = {
    "voltage": {"v": 1.0, "mv": 1e-3, "kv": 1e3},
    "current": {"a": 1.0, "ma": 1e-3, "ua": 1e-6},
    "power": {"w": 1.0, "mw": 1e-3, "kw": 1e3},
    "length": {"m": 1.0, "cm": 1e-2, "mm": 1e-3, "um": 1e-6, "in": 0.0254, "ft": 0.3048},
    "mass": {"kg": 1.0, "g": 1e-3, "mg": 1e-6, "lb": 0.45359237},
    "temperature_delta": {"c": 1.0, "k": 1.0, "f": 5.0 / 9.0},
}


def convert(value: int | float, from_unit: str, to_unit: str, dimension: str) -> float:
    """Convert compatible units to a target unit (temperature is delta-only)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("value must be a number, not bool")
    units = _FACTORS.get(dimension)
    if not units:
        raise ValueError(f"Unknown dimension: {dimension}")
    source, target = from_unit.strip().lower(), to_unit.strip().lower()
    if source not in units or target not in units:
        raise ValueError(f"Unsupported {dimension} units: {from_unit!r}, {to_unit!r}")
    return float(value) * units[source] / units[target]


def normalize_measurement(value: object, dimension: str, target_unit: str) -> float:
    """Read {'value': ..., 'unit': ...} and convert it to target_unit."""
    if not isinstance(value, dict) or "value" not in value or "unit" not in value:
        raise ValueError("measurement must contain value and unit")
    return convert(value["value"], str(value["unit"]), target_unit, dimension)
