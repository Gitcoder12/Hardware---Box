import struct

import pytest

from hardware_box.cad_mesh import analyze_mesh


def _write_binary_stl(path, triangles, declared_count=None):
    count = len(triangles) if declared_count is None else declared_count
    with path.open("wb") as stream:
        stream.write(b"HardwareBox edge tests".ljust(80, b" "))
        stream.write(struct.pack("<I", count))
        for triangle in triangles:
            stream.write(struct.pack("<3f", 0.0, 0.0, 0.0))
            for point in triangle:
                stream.write(struct.pack("<3f", *point))
            stream.write(struct.pack("<H", 0))


def test_reports_non_manifold_edge_and_aggregate_error_count(tmp_path):
    a, b = (0.0, 0.0, 0.0), (1.0, 0.0, 0.0)
    triangles = [
        (a, b, (0.0, 1.0, 0.0)),
        (b, a, (0.0, -1.0, 0.0)),
        (a, b, (0.0, 0.0, 1.0)),
    ]
    path = tmp_path / "non-manifold.stl"
    _write_binary_stl(path, triangles)
    report = analyze_mesh(path)
    assert report["manifold_errors"]["non_manifold_edges"] >= 1
    assert report["manifold_error_count"] == sum(report["manifold_errors"].values())
    assert report["volume"] is None


def test_rejects_truncated_binary_stl(tmp_path):
    path = tmp_path / "truncated.stl"
    _write_binary_stl(path, [], declared_count=1)
    with pytest.raises(ValueError, match="truncated binary STL"):
        analyze_mesh(path)


def test_counts_degenerate_triangles(tmp_path):
    path = tmp_path / "degenerate.stl"
    _write_binary_stl(path, [((0, 0, 0), (0, 0, 0), (0, 0, 0))])
    report = analyze_mesh(path)
    assert report["manifold_errors"]["degenerate_triangles"] == 1
    assert report["volume"] is None
