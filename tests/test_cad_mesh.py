import math
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from hardware_box.cad_mesh import analyze_mesh


def tetra_triangles():
    a = (0.0, 0.0, 0.0); b = (1.0, 0.0, 0.0)
    c = (0.0, 1.0, 0.0); d = (0.0, 0.0, 1.0)
    return [(a, c, b), (a, b, d), (a, d, c), (b, c, d)]


def write_binary_stl(path, triangles):
    with path.open("wb") as stream:
        stream.write(b"Hardware-Box test".ljust(80, b" "))
        stream.write(struct.pack("<I", len(triangles)))
        for tri in triangles:
            stream.write(struct.pack("<3f", 0, 0, 0))
            for point in tri:
                stream.write(struct.pack("<3f", *point))
            stream.write(struct.pack("<H", 0))


class CadMeshTests(unittest.TestCase):
    def test_closed_binary_stl_volume_and_edges(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tetra.stl"
            write_binary_stl(path, tetra_triangles())
            result = analyze_mesh(path, units="mm")
            self.assertEqual(result["encoding"], "binary")
            self.assertTrue(result["topology"]["watertight_by_edge_incidence"])
            self.assertTrue(result["topology"]["consistently_oriented_by_edge_direction"])
            self.assertAlmostEqual(result["volume"], 1 / 6, places=6)
            self.assertEqual(result["triangle_count"], 4)

    def test_open_mesh_has_no_volume_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "open.stl"
            write_binary_stl(path, [((0, 0, 0), (1, 0, 0), (0, 1, 0))])
            result = analyze_mesh(path)
            self.assertFalse(result["topology"]["watertight_by_edge_incidence"])
            self.assertEqual(result["topology"]["boundary_edge_count"], 3)
            self.assertIsNone(result["volume"])

    def test_disconnected_closed_shells_do_not_get_ambiguous_total_volume(self):
        first = tetra_triangles()
        second = [tuple((x + 3.0, y, z) for x, y, z in tri) for tri in tetra_triangles()]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "two-bodies.stl"
            write_binary_stl(path, first + second)
            result = analyze_mesh(path)
            self.assertTrue(result["topology"]["watertight_by_edge_incidence"])
            self.assertEqual(result["topology"]["edge_connected_component_count"], 2)
            self.assertIsNone(result["volume"])

    def test_3mf_mesh(self):
        model = '''<?xml version="1.0"?><model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><object id="1" type="model"><mesh><vertices><vertex x="0" y="0" z="0"/><vertex x="1" y="0" z="0"/><vertex x="0" y="1" z="0"/><vertex x="0" y="0" z="1"/></vertices><triangles><triangle v1="0" v2="2" v3="1"/><triangle v1="0" v2="1" v3="3"/><triangle v1="0" v2="3" v3="2"/><triangle v1="1" v2="2" v3="3"/></triangles></mesh></object></resources><build><item objectid="1"/></build></model>'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tetra.3mf"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("3D/3dmodel.model", model)
            result = analyze_mesh(path)
            self.assertEqual(result["format"], "3MF")
            self.assertEqual(result["units"], "millimeter")
            self.assertTrue(result["topology"]["watertight_by_edge_incidence"])
            self.assertAlmostEqual(result["volume"], 1 / 6, places=6)

    def test_3mf_declared_unit_is_read(self):
        model = '''<model unit="inch" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><object id="1"><mesh><vertices><vertex x="0" y="0" z="0"/><vertex x="1" y="0" z="0"/><vertex x="0" y="1" z="0"/></vertices><triangles><triangle v1="0" v2="1" v3="2"/></triangles></mesh></object></resources><build/></model>'''
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "unit-inch.3mf"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("3D/3dmodel.model", model)
            result = analyze_mesh(path)
            self.assertEqual(result["units"], "inch")
            self.assertEqual(result["model_declared_unit"], "inch")

    def test_bad_tolerance_and_format_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.stl"
            write_binary_stl(path, tetra_triangles())
            with self.assertRaises(ValueError):
                analyze_mesh(path, weld_tolerance=0)
            other = Path(tmp) / "a.step"
            other.write_text("ISO-10303-21;")
            with self.assertRaises(ValueError):
                analyze_mesh(other)


if __name__ == "__main__":
    unittest.main()
