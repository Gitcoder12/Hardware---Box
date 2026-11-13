"""Hardware-Box command line interface."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from .registry import add_device, update_device, get_device, list_devices, delete_device
from .validation import validate_device
from .compatibility import compare_devices
from .cad_inspector import inspect_model
from .manufacturing import suggest_processes
from .bom import export_bom_csv
from .assets import write_manifest, verify_manifest
from .audit import audit_project
from .schema_migrations import migrate_record
from .electrical import analyze_electrical
from .catalog import add_component, get_component, search_components
from .component_linker import link_bom_to_catalog
from .kicad import parse_kicad_bom_csv, inspect_kicad_netlist
from .kicad_native import inspect_kicad_native
from .kicad_audit import audit_kicad_exports
from .project_bundle import create_bundle, verify_bundle, extract_bundle
from .supply_chain import analyze_supply_chain, export_procurement_csv, cost_summary
from .design_review import review_design
from .eda_reports import inspect_kicad_report, audit_design_reports
from .kicad_checks import run_kicad_checks
from .cad_mesh import analyze_mesh
from .tolerance import analyze_tolerance_stack, analyze_clearance_fit, analyze_shaft_hole_fit


def _read(path: str | Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(data, path: str | Path):
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(prog="hardware-box", description="Local-first hardware engineering workbench")
    parser.add_argument("--db", default=".hardware-box/registry.sqlite3", help="Device registry database path")
    parser.add_argument("--catalog-db", default=".hardware-box/catalog.sqlite3", help="Component catalog database path")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize local device and component databases")
    p = sub.add_parser("add", help="Add a device JSON record"); p.add_argument("file")
    p = sub.add_parser("update", help="Replace an existing device JSON record"); p.add_argument("file")
    p = sub.add_parser("list", help="List registered devices"); p.add_argument("--category"); p.add_argument("--search")
    p = sub.add_parser("show", help="Show a device record"); p.add_argument("id")
    p = sub.add_parser("delete", help="Delete a device record"); p.add_argument("id"); p.add_argument("--yes", action="store_true")
    p = sub.add_parser("validate", help="Validate a device JSON record"); p.add_argument("file")
    p = sub.add_parser("migrate-record", help="Migrate a legacy device JSON record to schema v1"); p.add_argument("file"); p.add_argument("--output", default="migrated-device.json")
    p = sub.add_parser("compare", help="Compare declared interfaces between two device records"); p.add_argument("left"); p.add_argument("right")
    p = sub.add_parser("check-electrical", help="Run declared electrical budget checks"); p.add_argument("file")
    p = sub.add_parser("inspect-cad", help="Inspect STL, 3MF or STEP metadata"); p.add_argument("file")
    p = sub.add_parser("analyze-mesh", help="Analyze STL/3MF mesh topology, area and volume"); p.add_argument("file"); p.add_argument("--units"); p.add_argument("--weld-tolerance", type=float, default=1e-7); p.add_argument("--output")
    p = sub.add_parser("tolerance-stack", help="Analyze a unit-aware 1D tolerance stack from JSON"); p.add_argument("file"); p.add_argument("--output")
    p = sub.add_parser("fit-check", help="Analyze hole/shaft fit from JSON"); p.add_argument("file"); p.add_argument("--output"); p.add_argument("--statistical", action="store_true", help="Include normal-process RSS interference probability"); p.add_argument("--sigma-multiplier", type=float, default=3.0)
    p = sub.add_parser("suggest-fabrication", help="Suggest possible processes from CAD metadata"); p.add_argument("file")
    p = sub.add_parser("export-bom", help="Export a device BOM to CSV"); p.add_argument("id"); p.add_argument("--output", default="bom.csv")
    p = sub.add_parser("review", help="Run design documentation readiness checks"); p.add_argument("id")
    p = sub.add_parser("supply-chain", help="Analyze declared component sourcing risks"); p.add_argument("id")
    p = sub.add_parser("cost-summary", help="Summarize known BOM costs by currency"); p.add_argument("id")
    p = sub.add_parser("procurement", help="Export normalized procurement CSV"); p.add_argument("id"); p.add_argument("--output", default="procurement.csv")
    p = sub.add_parser("manifest", help="Create a SHA-256 asset manifest"); p.add_argument("--root", default="."); p.add_argument("--output", default="hardware-box-manifest.json")
    p = sub.add_parser("verify-manifest", help="Verify assets against a SHA-256 manifest"); p.add_argument("file", nargs="?", default="hardware-box-manifest.json"); p.add_argument("--root", default=".")
    p = sub.add_parser("audit", help="Audit device records and optionally asset integrity"); p.add_argument("--root", default="."); p.add_argument("--manifest", action="store_true")

    p = sub.add_parser("catalog-add", help="Add one component JSON record to the local catalog"); p.add_argument("file")
    p = sub.add_parser("catalog-show", help="Show an exact manufacturer part number"); p.add_argument("mpn")
    p = sub.add_parser("catalog-search", help="Search the local component catalog"); p.add_argument("query", nargs="?", default=""); p.add_argument("--category"); p.add_argument("--limit", type=int, default=100)
    p = sub.add_parser("catalog-link-device", help="Resolve device BOM part numbers against the local catalog"); p.add_argument("id")
    p = sub.add_parser("kicad-bom", help="Parse a KiCad BOM CSV into normalized JSON"); p.add_argument("file"); p.add_argument("--output", default="kicad-bom.json")
    p = sub.add_parser("inspect-netlist", help="Summarize a KiCad XML netlist"); p.add_argument("file"); p.add_argument("--output")
    p = sub.add_parser("inspect-kicad", help="Read-only inspect a native .kicad_sch or .kicad_pcb file"); p.add_argument("file"); p.add_argument("--output")
    p = sub.add_parser("audit-kicad", help="Cross-check KiCad BOM, netlist and optional native schematic/PCB references"); p.add_argument("bom"); p.add_argument("netlist"); p.add_argument("--schematic"); p.add_argument("--pcb"); p.add_argument("--output")
    p = sub.add_parser("inspect-eda-report", help="Inspect a KiCad ERC/DRC JSON report"); p.add_argument("file"); p.add_argument("--type", choices=["erc", "drc"]); p.add_argument("--output")
    p = sub.add_parser("audit-eda-reports", help="Combine available KiCad ERC/DRC JSON reports"); p.add_argument("--drc"); p.add_argument("--erc"); p.add_argument("--output")
    p = sub.add_parser("run-kicad-checks", help="Run read-only KiCad CLI ERC and/or DRC checks"); p.add_argument("--schematic"); p.add_argument("--pcb"); p.add_argument("--output-dir", default="hardware-box-reports"); p.add_argument("--executable", default="kicad-cli"); p.add_argument("--timeout", type=int, default=180); p.add_argument("--output")
    p = sub.add_parser("bundle-create", help="Create a portable integrity-checked project ZIP"); p.add_argument("--root", default="."); p.add_argument("--output", default="hardware-box-project.zip")
    p = sub.add_parser("bundle-verify", help="Verify a project bundle before sharing or extraction"); p.add_argument("file")
    p = sub.add_parser("bundle-extract", help="Verify and safely extract a project bundle"); p.add_argument("file"); p.add_argument("destination"); p.add_argument("--overwrite", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            from .registry import connect
            with connect(args.db): pass
            from .catalog import _connect
            db = _connect(args.catalog_db); db.close()
            print(json.dumps({"registry": args.db, "catalog": args.catalog_db, "status": "initialized"}, indent=2))
        elif args.command == "validate":
            errors = validate_device(_read(args.file))
            if errors: print("\n".join("ERROR: " + e for e in errors)); return 1
            print("VALID:", args.file)
        elif args.command == "migrate-record":
            record = migrate_record(_read(args.file)); errors = validate_device(record)
            if errors: print("\n".join("ERROR: " + e for e in errors)); return 1
            print("MIGRATED:", _write_json(record, args.output))
        elif args.command == "add": print("ADDED:", add_device(args.db, _read(args.file)))
        elif args.command == "update": update_device(args.db, _read(args.file)); print("UPDATED:", _read(args.file)["id"])
        elif args.command == "list":
            rows = list_devices(args.db, args.category, args.search)
            print(json.dumps([{"id": r["id"], "name": r["name"], "category": r["category"], "manufacturer": r["manufacturer"]} for r in rows], indent=2))
        elif args.command == "show":
            record = get_device(args.db, args.id)
            if record is None: print("NOT FOUND:", args.id); return 1
            print(json.dumps(record, indent=2))
        elif args.command == "delete":
            if not args.yes: print("Deletion not performed. Re-run with --yes to confirm."); return 2
            print("DELETED" if delete_device(args.db, args.id) else "NOT FOUND")
        elif args.command == "compare": print(json.dumps(compare_devices(_read(args.left), _read(args.right)), indent=2))
        elif args.command == "check-electrical":
            result = analyze_electrical(_read(args.file)); print(json.dumps(result, indent=2)); return 0 if result.get("valid") else 1
        elif args.command == "inspect-cad": print(json.dumps(inspect_model(args.file), indent=2))
        elif args.command == "analyze-mesh":
            result = analyze_mesh(args.file, args.units, args.weld_tolerance)
            if args.output: print("EXPORTED:", _write_json(result, args.output))
            else: print(json.dumps(result, indent=2))
        elif args.command == "tolerance-stack":
            payload = _read(args.file)
            result = analyze_tolerance_stack(payload.get("dimensions"), payload.get("default_unit", "mm"))
            result["name"] = payload.get("name")
            if args.output: print("EXPORTED:", _write_json(result, args.output))
            else: print(json.dumps(result, indent=2))
        elif args.command == "fit-check":
            payload = _read(args.file)
            result = (analyze_shaft_hole_fit(payload.get("hole"), payload.get("shaft"), payload.get("default_unit", "mm"), sigma_multiplier=args.sigma_multiplier) if args.statistical else analyze_clearance_fit(payload.get("hole"), payload.get("shaft"), payload.get("default_unit", "mm")))
            if args.output: print("EXPORTED:", _write_json(result, args.output))
            else: print(json.dumps(result, indent=2))
        elif args.command == "suggest-fabrication":
            info = inspect_model(args.file); print(json.dumps({"model": info, "suggestions": suggest_processes(info)}, indent=2))
        elif args.command in {"export-bom", "review", "supply-chain", "cost-summary", "procurement"}:
            record = get_device(args.db, args.id)
            if record is None: print("NOT FOUND:", args.id); return 1
            if args.command == "export-bom": output = export_bom_csv(record, args.output); print("EXPORTED:", output)
            elif args.command == "review": print(json.dumps(review_design(record), indent=2))
            elif args.command == "supply-chain": print(json.dumps(analyze_supply_chain(record), indent=2))
            elif args.command == "cost-summary": print(json.dumps(cost_summary(record), indent=2))
            elif args.command == "procurement": output = export_procurement_csv(record, args.output); print("EXPORTED:", output)
        elif args.command == "manifest": print("MANIFEST CREATED:", write_manifest(args.root, args.output))
        elif args.command == "verify-manifest":
            result = verify_manifest(args.root, args.file); print(json.dumps(result, indent=2)); return 0 if result["valid"] else 1
        elif args.command == "audit":
            result = audit_project(args.root, "hardware-box-manifest.json" if args.manifest else None); print(json.dumps(result, indent=2)); return 0 if result["valid"] else 1
        elif args.command == "catalog-add": print("CATALOG ADDED:", add_component(args.catalog_db, _read(args.file)))
        elif args.command == "catalog-show":
            item = get_component(args.catalog_db, args.mpn)
            if item is None: print("NOT FOUND:", args.mpn); return 1
            print(json.dumps(item, indent=2))
        elif args.command == "catalog-search": print(json.dumps(search_components(args.catalog_db, args.query, args.category, args.limit), indent=2))
        elif args.command == "catalog-link-device":
            record = get_device(args.db, args.id)
            if record is None: print("NOT FOUND:", args.id); return 1
            print(json.dumps(link_bom_to_catalog(args.catalog_db, record), indent=2))
        elif args.command == "kicad-bom": print("EXPORTED:", _write_json(parse_kicad_bom_csv(args.file), args.output))
        elif args.command == "inspect-netlist":
            result = inspect_kicad_netlist(args.file)
            if args.output: print("EXPORTED:", _write_json(result, args.output))
            else: print(json.dumps(result, indent=2))
        elif args.command == "inspect-kicad":
            result = inspect_kicad_native(args.file)
            if args.output: print("EXPORTED:", _write_json(result, args.output))
            else: print(json.dumps(result, indent=2))
        elif args.command == "audit-kicad":
            result = audit_kicad_exports(args.bom, args.netlist, args.schematic, args.pcb)
            if args.output: print("EXPORTED:", _write_json(result, args.output))
            else: print(json.dumps(result, indent=2))
            return 1 if result['status'] == 'fail' else 0
        elif args.command == "inspect-eda-report":
            result = inspect_kicad_report(args.file, args.type)
            if args.output: print("EXPORTED:", _write_json(result, args.output))
            else: print(json.dumps(result, indent=2))
            return 1 if result["status"] == "fail" else 2 if result["status"] == "review" else 0
        elif args.command == "audit-eda-reports":
            result = audit_design_reports(args.drc, args.erc)
            if args.output: print("EXPORTED:", _write_json(result, args.output))
            else: print(json.dumps(result, indent=2))
            return 1 if result["status"] == "fail" else 2 if result["status"] == "review" else 0
        elif args.command == "run-kicad-checks":
            result = run_kicad_checks(args.schematic, args.pcb, args.output_dir, args.executable, args.timeout)
            if args.output: print("EXPORTED:", _write_json(result, args.output))
            else: print(json.dumps(result, indent=2))
            return 1 if result["status"] == "fail" else 2 if result["status"] == "review" else 0
        elif args.command == "bundle-create": print(json.dumps(create_bundle(args.root, args.output), indent=2))
        elif args.command == "bundle-verify":
            result = verify_bundle(args.file); print(json.dumps(result, indent=2)); return 0 if result["valid"] else 1
        elif args.command == "bundle-extract": print(json.dumps(extract_bundle(args.file, args.destination, args.overwrite), indent=2))
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 1
    except Exception as exc:
        print(f"UNEXPECTED ERROR: {exc}", file=sys.stderr); return 1
    return 0


if __name__ == "__main__": raise SystemExit(main())
