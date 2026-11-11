"""Read-only ingestion and gating for KiCad ERC/DRC JSON reports.

The parser follows KiCad's published report structures. It preserves every
finding group and never silently drops unconnected or schematic-parity items.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

_DRC_GROUPS = ("violations", "unconnected_items", "schematic_parity")
_SEVERITIES = {"error", "warning", "exclusion"}


def _as_list(value: Any, label: str) -> list:
    if not isinstance(value, list):
        raise ValueError(f"{label}: expected an array in KiCad report")
    return value


def _normalise_violation(item: Any, group: str, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError(f"{group}[{index}]: expected an object")
    severity = str(item.get("severity", "")).strip().lower()
    if severity not in _SEVERITIES:
        raise ValueError(f"{group}[{index}]: unsupported or missing severity {severity!r}")
    raw_excluded = item.get("excluded", False)
    if not isinstance(raw_excluded, bool):
        raise ValueError(f"{group}[{index}].excluded: expected a boolean")
    excluded = raw_excluded or severity == "exclusion"
    affected = item.get("items", [])
    if not isinstance(affected, list):
        raise ValueError(f"{group}[{index}].items: expected an array")
    return {
        "group": group,
        "index": index,
        "type": str(item.get("type", "unknown")),
        "description": str(item.get("description", "")),
        "severity": severity,
        "excluded": excluded,
        "comment": str(item.get("comment", "")),
        "items": affected,
    }


def _summarise(kind: str, metadata: dict[str, Any], findings: list[dict[str, Any]], ignored_checks: list) -> dict[str, Any]:
    active = [item for item in findings if not item["excluded"]]
    excluded = [item for item in findings if item["excluded"]]
    counts = {level: sum(1 for item in active if item["severity"] == level)
              for level in ("error", "warning")}
    unknown_groups = sorted({item["group"] for item in findings if item["type"] == "unknown"})
    if counts["error"]:
        status = "fail"
    elif counts["warning"] or excluded or ignored_checks:
        status = "review"
    else:
        status = "pass"
    return {
        "report_type": kind,
        "status": status,
        "source": metadata.get("source"),
        "date": metadata.get("date"),
        "kicad_version": metadata.get("kicad_version"),
        "coordinate_units": metadata.get("coordinate_units"),
        "finding_count": len(findings),
        "active_finding_count": len(active),
        "excluded_finding_count": len(excluded),
        "severity_counts": counts,
        "ignored_check_count": len(ignored_checks),
        "ignored_checks": ignored_checks,
        "findings": findings,
        "limitations": [
            "This summarizes a supplied KiCad report; it does not run ERC/DRC itself.",
            "A clean report only reflects the checks, severities, and exclusions included by its producer.",
            "This parser does not independently validate electrical behavior or PCB manufacturability.",
        ],
    }


def parse_kicad_report(data: dict[str, Any], report_type: str | None = None) -> dict[str, Any]:
    """Normalize a KiCad ERC or DRC JSON report into a consistent summary."""
    if not isinstance(data, dict):
        raise ValueError("KiCad report root must be a JSON object")
    detected = report_type.lower() if report_type else None
    if detected is None:
        if any(key in data for key in _DRC_GROUPS):
            detected = "drc"
        elif "sheets" in data:
            detected = "erc"
        else:
            raise ValueError("Cannot identify report type: expected DRC groups or ERC sheets")
    if detected not in {"drc", "erc"}:
        raise ValueError("report_type must be 'erc' or 'drc'")

    findings: list[dict[str, Any]] = []
    ignored_checks = data.get("ignored_checks", [])
    if not isinstance(ignored_checks, list):
        raise ValueError("ignored_checks: expected an array")

    if detected == "drc":
        for group in _DRC_GROUPS:
            for index, violation in enumerate(_as_list(data.get(group), group)):
                findings.append(_normalise_violation(violation, group, index))
    else:
        sheets = _as_list(data.get("sheets"), "sheets")
        for sheet_index, sheet in enumerate(sheets):
            if not isinstance(sheet, dict):
                raise ValueError(f"sheets[{sheet_index}]: expected an object")
            sheet_path = str(sheet.get("path", ""))
            violations = _as_list(sheet.get("violations"), f"sheets[{sheet_index}].violations")
            for index, violation in enumerate(violations):
                normalized = _normalise_violation(violation, f"sheet:{sheet_path or sheet_index}", index)
                findings.append(normalized)

    return _summarise(detected, data, findings, ignored_checks)


def inspect_kicad_report(path: str | Path, report_type: str | None = None) -> dict[str, Any]:
    """Load and inspect a KiCad JSON report from disk."""
    source = Path(path)
    if source.stat().st_size > 128 * 1024 * 1024:
        raise ValueError("KiCad JSON report exceeds the 128 MiB safety limit")
    data = json.loads(source.read_text(encoding="utf-8"))
    result = parse_kicad_report(data, report_type)
    result["report_file"] = source.name
    result["report_size_bytes"] = source.stat().st_size
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    result["report_sha256"] = digest.hexdigest()
    return result


def audit_design_reports(drc_path: str | Path | None = None,
                         erc_path: str | Path | None = None) -> dict[str, Any]:
    """Combine available ERC/DRC reports; never interpret a missing report as pass."""
    if drc_path is None and erc_path is None:
        raise ValueError("Provide at least one of --drc or --erc")
    reports: dict[str, Any] = {}
    if drc_path is not None:
        reports["drc"] = inspect_kicad_report(drc_path, "drc")
    if erc_path is not None:
        reports["erc"] = inspect_kicad_report(erc_path, "erc")
    statuses = [report["status"] for report in reports.values()]
    status = "fail" if "fail" in statuses else "review" if "review" in statuses else "pass"
    return {
        "status": status,
        "reports_included": sorted(reports),
        "reports": reports,
        "disclaimer": "This gate summarizes only supplied KiCad reports. A missing report is not a pass, and a pass is not independent design certification.",
    }
