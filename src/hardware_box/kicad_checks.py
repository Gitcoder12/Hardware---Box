"""Optional, read-only execution of KiCad CLI ERC/DRC checks."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .eda_reports import audit_design_reports


def run_kicad_checks(schematic: str | Path | None = None,
                     pcb: str | Path | None = None,
                     output_dir: str | Path = "hardware-box-reports",
                     executable: str = "kicad-cli",
                     timeout_seconds: int = 180) -> dict[str, Any]:
    """Run KiCad CLI ERC/DRC and summarize reports; source design files stay untouched."""
    if schematic is None and pcb is None:
        raise ValueError("Provide a schematic and/or PCB path")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int) or timeout_seconds < 1:
        raise ValueError("timeout_seconds must be a positive integer")
    binary = shutil.which(executable)
    if binary is None:
        candidate = Path(executable)
        if candidate.is_file():
            binary = str(candidate.resolve())
        else:
            raise FileNotFoundError(f"KiCad CLI executable not found: {executable}")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    reports: dict[str, str] = {}
    commands: list[dict[str, Any]] = []

    jobs = []
    if schematic is not None:
        source = Path(schematic)
        if not source.is_file() or source.suffix.lower() != ".kicad_sch":
            raise ValueError(f"Schematic must be an existing .kicad_sch file: {source}")
        jobs.append(("erc", [binary, "sch", "erc", "--format", "json", "--severity-all",
                              "--output", str((out / f"{source.stem}-erc.json").resolve()), str(source.resolve())],
                     out / f"{source.stem}-erc.json"))
    if pcb is not None:
        source = Path(pcb)
        if not source.is_file() or source.suffix.lower() != ".kicad_pcb":
            raise ValueError(f"PCB must be an existing .kicad_pcb file: {source}")
        jobs.append(("drc", [binary, "pcb", "drc", "--format", "json", "--severity-all",
                              "--output", str((out / f"{source.stem}-drc.json").resolve()), str(source.resolve())],
                     out / f"{source.stem}-drc.json"))

    for kind, command, report_path in jobs:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds, check=False)
        commands.append({"check": kind, "returncode": completed.returncode,
                         "stdout": completed.stdout[-2000:], "stderr": completed.stderr[-2000:]})
        if completed.returncode != 0:
            raise RuntimeError(f"KiCad {kind.upper()} command failed with exit code {completed.returncode}: {completed.stderr.strip()}")
        if not report_path.is_file():
            raise RuntimeError(f"KiCad {kind.upper()} command did not create expected JSON report: {report_path}")
        reports[kind] = str(report_path)

    drc_path = reports.get("drc")
    erc_path = reports.get("erc")
    summary = audit_design_reports(drc_path=drc_path, erc_path=erc_path)
    summary["commands"] = commands
    summary["report_files"] = reports
    summary["execution_note"] = "KiCad CLI performed the requested checks. No save-board or zone-refill option was used; source design files are not intentionally modified."
    return summary
