import json
import tempfile
import unittest
from pathlib import Path

from hardware_box.eda_reports import parse_kicad_report, inspect_kicad_report, audit_design_reports


class EdaReportTests(unittest.TestCase):
    def test_drc_counts_all_three_finding_groups(self):
        report = {
            "source": "board.kicad_pcb", "kicad_version": "10.0",
            "violations": [{"type": "clearance", "description": "Too close", "severity": "error", "items": []}],
            "unconnected_items": [{"type": "unconnected", "description": "Airwire", "severity": "warning", "items": []}],
            "schematic_parity": [{"type": "parity", "description": "Missing footprint", "severity": "error", "items": []}],
        }
        result = parse_kicad_report(report)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["finding_count"], 3)
        self.assertEqual(result["severity_counts"], {"error": 2, "warning": 1})

    def test_warning_only_is_review_not_pass(self):
        report = {"violations": [], "unconnected_items": [], "schematic_parity": [
            {"type": "parity_warning", "description": "Review", "severity": "warning", "items": []}
        ]}
        self.assertEqual(parse_kicad_report(report)["status"], "review")

    def test_excluded_and_ignored_checks_are_visible(self):
        report = {"violations": [{"type": "clearance", "description": "Waived", "severity": "exclusion", "excluded": True, "items": []}],
                  "unconnected_items": [], "schematic_parity": [],
                  "ignored_checks": [{"key": "some_rule", "description": "Disabled by design"}]}
        result = parse_kicad_report(report)
        self.assertEqual(result["status"], "review")
        self.assertEqual(result["excluded_finding_count"], 1)
        self.assertEqual(result["ignored_check_count"], 1)

    def test_exclusions_alone_require_review(self):
        report = {"violations": [{"type": "waived", "description": "Excluded by user", "severity": "error", "excluded": True, "items": []}],
                  "unconnected_items": [], "schematic_parity": []}
        self.assertEqual(parse_kicad_report(report)["status"], "review")

    def test_erc_flattens_sheet_violations(self):
        report = {"source": "design.kicad_sch", "kicad_version": "10.0", "sheets": [
            {"path": "/", "violations": [
                {"type": "pin_not_driven", "description": "Un driven input", "severity": "error", "items": []}
            ]},
            {"path": "/power", "violations": []},
        ], "ignored_checks": []}
        result = parse_kicad_report(report)
        self.assertEqual(result["report_type"], "erc")
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["findings"][0]["group"], "sheet:/")

    def test_invalid_report_does_not_silently_pass(self):
        with self.assertRaises(ValueError):
            parse_kicad_report({"violations": []})
        with self.assertRaises(ValueError):
            parse_kicad_report({"sheets": [{"violations": [{"type": "bad", "description": "x", "items": []}]}]})

    def test_file_and_combined_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            drc = Path(tmp) / "drc.json"
            erc = Path(tmp) / "erc.json"
            drc.write_text(json.dumps({"violations": [], "unconnected_items": [], "schematic_parity": []}))
            erc.write_text(json.dumps({"sheets": [], "ignored_checks": []}))
            inspected = inspect_kicad_report(drc)
            self.assertEqual(inspected["status"], "pass")
            self.assertEqual(len(inspected["report_sha256"]), 64)
            self.assertEqual(audit_design_reports(drc, erc)["status"], "pass")
        with self.assertRaises(ValueError):
            audit_design_reports()


if __name__ == "__main__":
    unittest.main()
