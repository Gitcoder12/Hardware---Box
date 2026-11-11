"""Integration tests over the checked-in sample KiCad project."""
import unittest
from pathlib import Path
from hardware_box.kicad_native import inspect_kicad_native
from hardware_box.kicad_audit import audit_kicad_exports

ROOT = Path(__file__).resolve().parents[1]


class KiCadExampleIntegrationTests(unittest.TestCase):
    def test_native_schematic_example(self):
        result = inspect_kicad_native(ROOT / "examples/kicad-native/controller.kicad_sch")
        self.assertEqual(result["references"], ["C1", "R1", "U1"])
        self.assertEqual(result["placed_symbol_count"], 3)

    def test_native_pcb_example(self):
        result = inspect_kicad_native(ROOT / "examples/kicad-native/controller.kicad_pcb")
        self.assertEqual(result["footprint_count"], 3)
        self.assertEqual(result["pad_count"], 8)
        self.assertEqual(result["net_count"], 3)
        self.assertEqual(result["track_segment_count"], 2)
        self.assertEqual(result["track_arc_count"], 1)

    def test_cross_file_example_audit_passes(self):
        result = audit_kicad_exports(
            ROOT / "examples/kicad/bom.csv",
            ROOT / "examples/kicad/netlist.xml",
            ROOT / "examples/kicad-native/controller.kicad_sch",
            ROOT / "examples/kicad-native/controller.kicad_pcb",
        )
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["pcb_pad_net_comparisons"], 8)
        self.assertEqual(result["severity_counts"], {"high": 0, "medium": 0, "low": 0, "info": 0})


if __name__ == "__main__":
    unittest.main()
