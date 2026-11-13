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

def test_reversed_duplicate_face_is_not_reported_as_watertight(tmp_path):
    triangle = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    reversed_triangle = (triangle[0], triangle[2], triangle[1])
    path = tmp_path / "duplicate-opposite-faces.stl"
    _write_binary_stl(path, [triangle, reversed_triangle])
    report = analyze_mesh(path)
    assert report["manifold_errors"]["duplicate_triangles"] == 1
    assert report["manifold_error_count"] >= 1
    assert report["topology"]["watertight_by_edge_incidence"] is False
    assert report["volume"] is None


def test_rejects_non_utf8_ascii_stl_with_clear_error(tmp_path):
    path = tmp_path / "invalid-ascii.stl"
    path.write_bytes(b"solid malformed\n\xff\n")
    with pytest.raises(ValueError, match="neither a valid binary STL nor UTF-8 ASCII STL"):
        analyze_mesh(path)


def test_rejects_corrupted_3mf_zip(tmp_path):
    path = tmp_path / "corrupt.3mf"
    path.write_bytes(b"not a zip archive")
    with pytest.raises(ValueError, match="Invalid or corrupted 3MF archive"):
        analyze_mesh(path)


def test_rejects_malformed_3mf_vertex_coordinates(tmp_path):
    import zipfile

    model = (
        '<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        '<resources><object id="1"><mesh><vertices>'
        '<vertex x="not-a-number" y="0" z="0"/>'
        '</vertices><triangles><triangle v1="0" v2="0" v3="0"/>'
        '</triangles></mesh></object></resources></model>'
    )
    path = tmp_path / "bad-coordinate.3mf"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("3D/3dmodel.model", model)
    with pytest.raises(ValueError, match="missing or invalid coordinates"):
        analyze_mesh(path)
