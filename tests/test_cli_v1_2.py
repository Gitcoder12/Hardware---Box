import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from hardware_box.cli import main


class CliV12Tests(unittest.TestCase):
    def test_inspect_eda_report_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "drc.json"
            source.write_text(json.dumps({"violations": [], "unconnected_items": [], "schematic_parity": []}))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["inspect-eda-report", str(source)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue())["status"], "pass")

    def test_tolerance_stack_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "stack.json"
            source.write_text(json.dumps({"dimensions": [{"nominal": 12.0, "tolerance_plus": 0.1, "tolerance_minus": 0.1}]}))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["tolerance-stack", str(source)])
            self.assertEqual(code, 0)
            self.assertAlmostEqual(json.loads(output.getvalue())["nominal_mm"], 12.0)

    def test_mesh_command_with_checked_in_sample(self):
        root = Path(__file__).resolve().parents[1]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["analyze-mesh", str(root / "examples/mechanical/tetrahedron.stl"), "--units", "mm"])
        self.assertEqual(code, 0)
        result = json.loads(output.getvalue())
        self.assertTrue(result["topology"]["watertight_by_edge_incidence"])
        self.assertAlmostEqual(result["volume"], 1 / 6, places=6)

    def test_fit_check_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "fit.json"
            source.write_text(json.dumps({"hole": {"nominal": 10.1}, "shaft": {"nominal": 10.0}}))
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(["fit-check", str(source)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue())["fit_type"], "clearance")


if __name__ == "__main__":
    unittest.main()
