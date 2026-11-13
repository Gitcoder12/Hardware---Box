"""Read-only triangle-mesh quality metrics for STL and 3MF files.

This is mesh topology/geometry screening, not CAD-kernel repair, solid modeling,
or proof that an exported mesh matches its source CAD model.
"""
from __future__ import annotations

import math
import struct
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Iterable


def _finite_point(point: tuple[float, float, float]) -> bool:
    return all(math.isfinite(value) for value in point)


def _stl_triangles(path: Path) -> tuple[str, Iterable[tuple[tuple[float, float, float], ...]]]:
    size = path.stat().st_size
    with path.open("rb") as stream:
        header = stream.read(84)
        if len(header) >= 84:
            count = struct.unpack_from("<I", header, 80)[0]
            if 84 + count * 50 == size:
                def binary_iter():
                    with path.open("rb") as source:
                        source.seek(84)
                        for _ in range(count):
                            record = source.read(50)
                            if len(record) != 50:
                                raise ValueError("Truncated binary STL triangle record")
                            values = struct.unpack_from("<12f", record, 0)
                            triangle = (tuple(values[3:6]), tuple(values[6:9]), tuple(values[9:12]))
                            if not all(_finite_point(p) for p in triangle):
                                raise ValueError("STL contains non-finite vertex coordinates")
                            yield triangle
                return "binary", binary_iter()
            if not header[:80].lstrip().lower().startswith(b"solid"):
                raise ValueError(
                    "Malformed or truncated binary STL: triangle count does not match file size"
                )

    def ascii_iter():
        pending = []
        try:
            with path.open("r", encoding="utf-8", errors="strict") as source:
                for line_number, line in enumerate(source, start=1):
                    parts = line.strip().split()
                    if len(parts) == 4 and parts[0].lower() == "vertex":
                        try:
                            point = tuple(float(value) for value in parts[1:])
                        except ValueError as exc:
                            raise ValueError(f"Invalid STL vertex at line {line_number}") from exc
                        if len(point) != 3 or not _finite_point(point):
                            raise ValueError(f"Non-finite or malformed STL vertex at line {line_number}")
                        pending.append(point)
                        if len(pending) == 3:
                            yield tuple(pending)
                            pending.clear()
        except UnicodeDecodeError as exc:
            raise ValueError("STL is neither a valid binary STL nor UTF-8 ASCII STL") from exc
        if pending:
            raise ValueError("ASCII STL has an incomplete triangle (vertex count is not divisible by 3)")
    return "ascii", ascii_iter()


def _3mf_triangles(path: Path) -> tuple[str, str, Iterable[tuple[tuple[float, float, float], ...]]]:
    try:
        with zipfile.ZipFile(path) as archive:
            candidates = [name for name in archive.namelist() if name.lower().endswith(".model")]
            if not candidates:
                raise ValueError("3MF archive contains no model file")
            preferred = next((name for name in candidates if name.lower() == "3d/3dmodel.model"), candidates[0])
            info = archive.getinfo(preferred)
            if info.file_size > 256 * 1024 * 1024:
                raise ValueError("3MF model XML exceeds the 256 MiB safety limit")
            root = ET.fromstring(archive.read(preferred))
    except (zipfile.BadZipFile, ET.ParseError, OSError) as exc:
        raise ValueError(f"Invalid or corrupted 3MF archive: {exc}") from exc

    model_unit = root.attrib.get("unit", "millimeter").lower()
    allowed_units = {"micron", "millimeter", "centimeter", "inch", "foot", "meter"}
    if model_unit not in allowed_units:
        raise ValueError(f"Unsupported 3MF model unit: {model_unit!r}")
    all_meshes = root.findall(".//{*}mesh")
    def model_iter():
        found = False
        for mesh in all_meshes:
            vertices_node = mesh.find("{*}vertices")
            triangles_node = mesh.find("{*}triangles")
            if vertices_node is None or triangles_node is None:
                continue
            vertices = []
            for vertex in vertices_node.findall("{*}vertex"):
                try:
                    point = (
                        float(vertex.attrib["x"]),
                        float(vertex.attrib["y"]),
                        float(vertex.attrib["z"]),
                    )
                except (KeyError, ValueError) as exc:
                    raise ValueError("3MF vertex has missing or invalid coordinates") from exc
                if not _finite_point(point):
                    raise ValueError("3MF contains non-finite vertex coordinates")
                vertices.append(point)
            for triangle in triangles_node.findall("{*}triangle"):
                try:
                    indices = [int(triangle.attrib[key]) for key in ("v1", "v2", "v3")]
                    points = tuple(vertices[index] for index in indices)
                except (KeyError, ValueError, IndexError) as exc:
                    raise ValueError("3MF triangle references an invalid vertex") from exc
                found = True
                yield points
        if not found:
            raise ValueError("3MF model contains no readable mesh triangles")
    return preferred, model_unit, model_iter()


def _mesh_key(point: tuple[float, float, float], tolerance: float) -> tuple[int, int, int]:
    return tuple(int(round(value / tolerance)) for value in point)


def _analyze_triangles(triangles: Iterable[tuple[tuple[float, float, float], ...]],
                       weld_tolerance: float, units: str, source_format: str) -> dict:
    edge_stats: dict[tuple[tuple[int, int, int], tuple[int, int, int]], list[int]] = {}
    face_parent: list[int] = []
    component_signed_volumes: dict[int, float] = {}

    def find_face(face: int) -> int:
        while face_parent[face] != face:
            face_parent[face] = face_parent[face_parent[face]]
            face = face_parent[face]
        return face

    def union_faces(left: int, right: int) -> None:
        root_left, root_right = find_face(left), find_face(right)
        if root_left != root_right:
            face_parent[root_right] = root_left
    vertex_values: dict[tuple[int, int, int], tuple[float, float, float]] = {}
    face_counts: Counter = Counter()
    mins = [math.inf, math.inf, math.inf]
    maxs = [-math.inf, -math.inf, -math.inf]
    triangle_count = 0
    degenerate_count = 0
    surface_area = 0.0

    for triangle in triangles:
        if len(triangle) != 3 or not all(_finite_point(point) for point in triangle):
            raise ValueError("Mesh contains an invalid triangle or non-finite coordinate")
        face_index = triangle_count
        triangle_count += 1
        face_parent.append(face_index)
        keys = [_mesh_key(point, weld_tolerance) for point in triangle]
        for key, point in zip(keys, triangle):
            vertex_values.setdefault(key, point)
            for axis in range(3):
                mins[axis] = min(mins[axis], point[axis])
                maxs[axis] = max(maxs[axis], point[axis])
        face_counts[tuple(sorted(keys))] += 1

        a, b, c = triangle
        ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        cross = (ab[1] * ac[2] - ab[2] * ac[1],
                 ab[2] * ac[0] - ab[0] * ac[2],
                 ab[0] * ac[1] - ab[1] * ac[0])
        area = 0.5 * math.sqrt(sum(value * value for value in cross))
        if area <= weld_tolerance * weld_tolerance:
            degenerate_count += 1
        else:
            surface_area += area
        face_volume = (a[0] * (b[1] * c[2] - b[2] * c[1])
                       + a[1] * (b[2] * c[0] - b[0] * c[2])
                       + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
        component_signed_volumes[face_index] = face_volume

        for start, end in ((keys[0], keys[1]), (keys[1], keys[2]), (keys[2], keys[0])):
            if start == end:
                continue
            edge = (start, end) if start < end else (end, start)
            direction = 1 if start < end else -1
            entry = edge_stats.get(edge)
            if entry is None:
                edge_stats[edge] = [1, direction, face_index]
            else:
                entry[0] += 1
                entry[1] += direction
                union_faces(face_index, entry[2])

    if triangle_count == 0:
        raise ValueError("Mesh contains no triangles")
    edge_counts = Counter(value[0] for value in edge_stats.values())
    boundary_edges = edge_counts.get(1, 0)
    non_manifold_edges = sum(count for uses, count in edge_counts.items() if uses > 2)
    inconsistent_edges = sum(1 for uses, direction_sum, _first_face in edge_stats.values() if uses == 2 and direction_sum != 0)
    duplicate_faces = sum(count - 1 for count in face_counts.values() if count > 1)
    # Duplicate coincident faces make the enclosed surface ambiguous even when
    # each edge happens to have two uses (e.g. a single face plus its reverse).
    watertight = (
        boundary_edges == 0
        and non_manifold_edges == 0
        and degenerate_count == 0
        and duplicate_faces == 0
    )
    consistently_oriented = inconsistent_edges == 0
    component_totals: dict[int, float] = {}
    for face_index, face_volume in component_signed_volumes.items():
        root = find_face(face_index)
        component_totals[root] = component_totals.get(root, 0.0) + face_volume
    connected_components = len(component_totals)
    # Do not sum disconnected shells: separate shell winding can cancel or represent cavities.
    volume = abs(next(iter(component_totals.values()))) if (watertight and consistently_oriented and connected_components == 1) else None

    manifold_errors = {
        "boundary_edges": boundary_edges,
        "non_manifold_edges": non_manifold_edges,
        "inconsistent_orientation_edges": inconsistent_edges,
        "degenerate_triangles": degenerate_count,
        "duplicate_triangles": duplicate_faces,
    }
    return {
        "format": source_format,
        "triangle_count": triangle_count,
        "unique_vertex_count": len(vertex_values),
        "unique_edge_count": len(edge_stats),
        "bounds": {
            axis: {"min": round(mins[i], 9), "max": round(maxs[i], 9), "size": round(maxs[i] - mins[i], 9)}
            for i, axis in enumerate(("x", "y", "z"))
        },
        "surface_area": round(surface_area, 9),
        "volume": round(volume, 9) if volume is not None else None,
        "volume_status": "computed_for_single_closed_consistently_oriented_shell" if volume is not None else "not_computed_mesh_not_closed_or_oriented_or_has_multiple_shells",
        "manifold_errors": manifold_errors,
        "manifold_error_count": sum(manifold_errors.values()),
        "topology": {
            "watertight_by_edge_incidence": watertight,
            "consistently_oriented_by_edge_direction": consistently_oriented,
            "boundary_edge_count": boundary_edges,
            "non_manifold_edge_count": non_manifold_edges,
            "edge_connected_component_count": connected_components,
            "inconsistent_orientation_edge_count": inconsistent_edges,
            "degenerate_triangle_count": degenerate_count,
            "duplicate_triangle_count": duplicate_faces,
        },
        "units": units,
        "surface_area_unit": f"{units}^2",
        "volume_unit": f"{units}^3" if volume is not None else None,
        "weld_tolerance": weld_tolerance,
        "weld_tolerance_unit": units,
        "limitations": [
            "Mesh-only diagnostics; no CAD-kernel B-rep topology or geometric repair is performed.",
            "STL units are not encoded reliably; provide --units only when the source unit is known.",
            "3MF component/build transforms are not applied; metrics summarize object mesh definitions.",
            "Watertightness is inferred from welded triangle-edge incidence and does not prove printability or dimensional accuracy.",
        ],
    }


def analyze_mesh(path: str | Path, units: str | None = None, weld_tolerance: float = 1e-7) -> dict:
    """Analyze STL or 3MF mesh area, bounds, edge closure and volume."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    if isinstance(weld_tolerance, bool) or not isinstance(weld_tolerance, (int, float)) or not math.isfinite(float(weld_tolerance)) or weld_tolerance <= 0:
        raise ValueError("weld_tolerance must be a positive finite number")
    extension = source.suffix.lower()
    if extension == ".stl":
        encoding, triangles = _stl_triangles(source)
        result = _analyze_triangles(triangles, float(weld_tolerance), units or "unknown", "STL")
        result["encoding"] = encoding
    elif extension == ".3mf":
        model_entry, model_unit, triangles = _3mf_triangles(source)
        result = _analyze_triangles(triangles, float(weld_tolerance), units or model_unit, "3MF")
        result["model_declared_unit"] = model_unit
        result["model_entry"] = model_entry
    else:
        raise ValueError("Mesh analysis supports .stl and .3mf; STEP requires a CAD kernel")
    result["file"] = source.name
    result["size_bytes"] = source.stat().st_size
    return result
