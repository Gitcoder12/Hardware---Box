"""Explainable documentation-readiness checks (not engineering certification)."""
from __future__ import annotations
from typing import Any

from .supply_chain import analyze_supply_chain
from .validation import validate_device


def review_design(record: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic record and sourcing completeness checks."""
    errors = validate_device(record)
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    add("record_schema", not errors,
        "Record passes the current schema." if not errors else "; ".join(errors))
    components = record.get("components", []) if isinstance(record.get("components", []), list) else []
    interfaces = record.get("interfaces", []) if isinstance(record.get("interfaces", []), list) else []
    provenance = record.get("provenance", {}) if isinstance(record.get("provenance", {}), dict) else {}
    add("component_inventory", bool(components), f"{len(components)} component line(s) declared.")
    add("interfaces_documented", bool(interfaces), f"{len(interfaces)} interface(s) declared.")
    add("source_recorded", bool(provenance.get("source")),
        "Source recorded." if provenance.get("source") else "Add a source URL, datasheet, drawing, or controlled document reference.")
    add("license_recorded", bool(provenance.get("license")),
        "License recorded." if provenance.get("license") else "Clarify redistribution rights.")
    level = provenance.get("verification")
    add("verification_claim", level in {"documented", "verified"},
        f"Verification level: {level or 'missing'}. Human evidence review is still required.")
    sourcing = analyze_supply_chain(record)
    add("sourcing_review", sourcing["severity_counts"]["high"] == 0,
        f"{sourcing['finding_count']} sourcing finding(s): {sourcing['severity_counts']}.")
    passed = sum(check["passed"] for check in checks)
    return {
        "device_id": record.get("id"),
        "readiness_score": round(100 * passed / len(checks)) if checks else 0,
        "passed_checks": passed,
        "total_checks": len(checks),
        "checks": checks,
        "supply_chain": sourcing,
        "disclaimer": "Documentation checklist only; not safety, compliance, electrical, thermal, structural, or manufacturability certification.",
    }
