import json, tempfile, unittest
from pathlib import Path
from hardware_box.cli import main
ROOT = Path(__file__).resolve().parents[1]

class CLITests(unittest.TestCase):
    def test_init_add_and_catalog_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / 'devices.sqlite3'); cdb = str(Path(tmp) / 'catalog.sqlite3')
            self.assertEqual(main(['--db', db, '--catalog-db', cdb, 'init']), 0)
            self.assertEqual(main(['--db', db, 'add', str(ROOT / 'database/devices/example-controller.json')]), 0)
            self.assertEqual(main(['--db', db, 'review', 'example-controller']), 0)
    def test_migrate_record_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'migrated.json'
            self.assertEqual(main(['migrate-record', str(ROOT / 'database/devices/example-controller.json'), '--output', str(output)]), 0)
            self.assertEqual(json.loads(output.read_text())['schema_version'], 1)
    def test_bundle_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'; root.mkdir(); (root / 'readme').write_text('ok')
            bundle = Path(tmp) / 'project.zip'
            self.assertEqual(main(['bundle-create', '--root', str(root), '--output', str(bundle)]), 0)
            self.assertEqual(main(['bundle-verify', str(bundle)]), 0)


class KiCadCLITests(unittest.TestCase):
    def test_native_inspection_and_export_audit_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            schematic = root / "design.kicad_sch"
            schematic.write_text('(kicad_sch (version 20250114) (generator "eeschema") (symbol (lib_id "Device:R") (property "Reference" "R1") (property "Value" "10k")))', encoding="utf-8")
            board = root / "design.kicad_pcb"
            board.write_text('(kicad_pcb (version 20241229) (generator "pcbnew") (layers (0 "F.Cu" signal)) (net 1 "GND") (footprint "R_0603" (property "Reference" "R1") (property "Value" "10k") (pad "1" smd rect (net 1 "GND")) (pad "2" smd rect (net 1 "GND"))))', encoding="utf-8")
            bom = root / "bom.csv"
            bom.write_text('References,Value\nR1,10k\n', encoding="utf-8")
            netlist = root / "board.net"
            netlist.write_text('<export><components><comp ref="R1"><value>10k</value></comp></components><nets><net code="1" name="GND"><node ref="R1" pin="1"/><node ref="R1" pin="2"/></net></nets></export>', encoding="utf-8")
            out = root / "native.json"
            self.assertEqual(main(["inspect-kicad", str(schematic), "--output", str(out)]), 0)
            self.assertEqual(json.loads(out.read_text())['placed_symbol_count'], 1)
            report = root / "audit.json"
            self.assertEqual(main(["audit-kicad", str(bom), str(netlist), "--schematic", str(schematic), "--pcb", str(board), "--output", str(report)]), 0)
            result = json.loads(report.read_text())
            self.assertTrue(result['native_schematic_inspected'])
            self.assertTrue(result['native_pcb_inspected'])
            self.assertEqual(result['status'], 'pass')
