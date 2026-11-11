import json
import os
import tempfile
import unittest
from pathlib import Path

from hardware_box.kicad_checks import run_kicad_checks


class KiCadChecksTests(unittest.TestCase):
    def test_fake_cli_runs_erc_and_drc_without_touching_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schematic = root / "design.kicad_sch"; schematic.write_text("(kicad_sch (version 1))")
            pcb = root / "design.kicad_pcb"; pcb.write_text("(kicad_pcb (version 1))")
            executable = root / "fake-kicad-cli"
            executable.write_text('''#!/usr/bin/env python3
import json, pathlib, sys
args = sys.argv[1:]
out = pathlib.Path(args[args.index("--output") + 1])
if args[0] == "pcb":
    payload = {"source":"design.kicad_pcb","date":"2026-01-01T00:00:00Z","kicad_version":"10.0","violations":[],"unconnected_items":[],"schematic_parity":[]}
else:
    payload = {"source":"design.kicad_sch","date":"2026-01-01T00:00:00Z","kicad_version":"10.0","sheets":[],"ignored_checks":[]}
out.write_text(json.dumps(payload))
''')
            executable.chmod(0o755)
            result = run_kicad_checks(schematic, pcb, root / "reports", str(executable))
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["reports_included"], ["drc", "erc"])
            self.assertEqual(schematic.read_text(), "(kicad_sch (version 1))")
            self.assertEqual(pcb.read_text(), "(kicad_pcb (version 1))")

    def test_missing_cli_rejected(self):
        with self.assertRaises(FileNotFoundError):
            run_kicad_checks(schematic="missing.kicad_sch", executable="no-such-kicad-cli")

    def test_no_input_rejected(self):
        with self.assertRaises(ValueError):
            run_kicad_checks()


if __name__ == "__main__":
    unittest.main()
