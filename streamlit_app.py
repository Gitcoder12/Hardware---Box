"""Hardware-Box: read-only hardware engineering workbench."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import struct
import zipfile
from pathlib import PurePosixPath

import streamlit as st

st.set_page_config(page_title="Hardware-Box", page_icon="🔧", layout="wide")
st.title("🔧 Hardware-Box")
st.caption("Open-source engineering workbench · read-only analysis · Apache-2.0")

with st.sidebar:
    page = st.radio("Workspace", [
        "Overview", "Device records", "Tolerance & fit",
        "STL inspection", "KiCad BOM", "Project integrity"
    ])
    st.caption("Uploaded files are processed in memory and are not saved by this app.")

def report_download(data, name):
    st.download_button("Download JSON report", json.dumps(data, indent=2),
                       file_name=name, mime="application/json",
                       use_container_width=True)

def parse_stl(data: bytes):
    triangles = []
    if len(data) >= 84:
        count = struct.unpack_from("<I", data, 80)[0]
        if 84 + count * 50 == len(data):
            for i in range(count):
                v = struct.unpack_from("<12fH", data, 84 + i * 50)
                triangles.append([v[3:6], v[6:9], v[9:12]])
    if not triangles:
        text = data.decode("utf-8")
        vertices = []
        for line in text.splitlines():
            p = line.strip().split()
            if len(p) == 4 and p[0].lower() == "vertex":
                vertices.append(tuple(map(float, p[1:])))
        if not vertices or len(vertices) % 3:
            raise ValueError("No complete STL triangle groups found.")
        triangles = [vertices[i:i+3] for i in range(0, len(vertices), 3)]
    points = [p for triangle in triangles for p in triangle]
    lo = [min(p[i] for p in points) for i in range(3)]
    hi = [max(p[i] for p in points) for i in range(3)]
    degenerate, volume = 0, 0.0
    for a, b, c in triangles:
        ab = [b[i]-a[i] for i in range(3)]
        ac = [c[i]-a[i] for i in range(3)]
        cross = (ab[1]*ac[2]-ab[2]*ac[1],
                 ab[2]*ac[0]-ab[0]*ac[2],
                 ab[0]*ac[1]-ab[1]*ac[0])
        degenerate += sum(x*x for x in cross) < 1e-20
        volume += (a[0]*(b[1]*c[2]-b[2]*c[1])
                   + a[1]*(b[2]*c[0]-b[0]*c[2])
                   + a[2]*(b[0]*c[1]-b[1]*c[0])) / 6
    return {
        "triangles": len(triangles), "vertices": len(points),
        "bounds_min": lo, "bounds_max": hi,
        "size": [hi[i]-lo[i] for i in range(3)],
        "degenerate_triangles": int(degenerate),
        "signed_mesh_volume_estimate": volume,
        "note": "Triangle-soup estimate only. Confirm watertightness and orientation in CAD."
    }

def inspect_zip(data: bytes):
    result = {"valid_zip": False, "files": [], "unsafe_paths": [], "total_bytes": 0}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for item in zf.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in item.filename:
                result["unsafe_paths"].append(item.filename)
            elif not item.is_dir():
                result["files"].append({"path": item.filename, "bytes": item.file_size})
                result["total_bytes"] += item.file_size
    result["valid_zip"] = not result["unsafe_paths"]
    return result

if page == "Overview":
    st.subheader("Understand hardware. Verify the details.")
    st.write("Inspect device records, calculate tolerance stacks, review mechanical meshes and PCB bills of materials, and verify project bundles.")
    cols = st.columns(4)
    for col, (label, value) in zip(cols, [
        ("Device data", "JSON"), ("Mechanical", "STL"),
        ("PCB", "KiCad BOM"), ("Integrity", "SHA-256")
    ]):
        col.metric(label, value)
    st.markdown("""
    - **Device records:** validate structured device metadata.
    - **Tolerance & fit:** worst-case and RSS stack calculations; hole/shaft fit.
    - **STL inspection:** mesh bounds, triangle count and degenerate facets.
    - **KiCad BOM:** component rows, duplicate references and missing values.
    - **Project integrity:** ZIP path-safety scan and SHA-256 digest.
    """)
    st.info("Engineering support only. Results do not replace CAD validation, simulation, ERC/DRC, GD&T or manufacturing sign-off.")

elif page == "Device records":
    st.subheader("Device record validation")
    upload = st.file_uploader("Upload device JSON", type=["json"])
    if upload:
        try:
            obj = json.loads(upload.getvalue())
            errors = [f"Missing or empty: {key}" for key in
                      ("id", "name", "category", "manufacturer")
                      if not isinstance(obj.get(key), str) or not obj[key].strip()]
            if "components" in obj and not isinstance(obj["components"], list):
                errors.append("components must be an array")
            if errors:
                st.error("Record needs correction")
                for error in errors:
                    st.write(f"- {error}")
            else:
                st.success("Record structure is valid")
                a, b, c = st.columns(3)
                a.metric("Device", obj["name"])
                b.metric("Components", len(obj.get("components", [])))
                c.metric("Fields", len(obj))
                st.json(obj)
                report_download({
                    "valid": True, "device": obj,
                    "sha256": hashlib.sha256(upload.getvalue()).hexdigest()
                }, "device-review.json")
        except Exception as exc:
            st.error(f"Could not read JSON: {exc}")
    else:
        st.code('{"id":"controller-001","name":"Example Controller","category":"embedded","manufacturer":"Example Labs","components":[]}', language="json")

elif page == "Tolerance & fit":
    st.subheader("Tolerance stack analysis")
    unit = st.selectbox("Unit", ["mm", "cm", "in"])
    mode = st.radio("Analysis", ["Tolerance stack", "Hole / shaft fit"], horizontal=True)
    if mode == "Tolerance stack":
        raw = st.text_area("Dimensions JSON", json.dumps({"dimensions": [
            {"name": "A", "nominal": 20, "tolerance": 0.10},
            {"name": "B", "nominal": 10, "tolerance": 0.05},
            {"name": "C", "nominal": 5, "tolerance": 0.02}
        ]}, indent=2), height=190)
        if st.button("Calculate stack", type="primary"):
            try:
                dims = json.loads(raw)["dimensions"]
                if not isinstance(dims, list) or not dims:
                    raise ValueError("dimensions must be a non-empty list")
                nominal = sum(float(d["nominal"]) for d in dims)
                worst = sum(abs(float(d["tolerance"])) for d in dims)
                rss = math.sqrt(sum(float(d["tolerance"])**2 for d in dims))
                result = {"unit": unit, "contributors": len(dims), "nominal": nominal,
                          "worst_case": [nominal-worst, nominal+worst], "rss_tolerance": rss}
                a, b, c = st.columns(3)
                a.metric("Nominal", f"{nominal:g} {unit}")
                b.metric("Worst-case range", f"{nominal-worst:g} – {nominal+worst:g} {unit}")
                c.metric("RSS tolerance", f"±{rss:.4g} {unit}")
                report_download(result, "tolerance-stack.json")
            except Exception as exc:
                st.error(f"Invalid dimensions: {exc}")
    else:
        a, b = st.columns(2)
        with a:
            st.markdown("**Hole**")
            hmin = st.number_input("Hole minimum", value=10.0)
            hmax = st.number_input("Hole maximum", value=10.1)
        with b:
            st.markdown("**Shaft**")
            smin = st.number_input("Shaft minimum", value=9.95)
            smax = st.number_input("Shaft maximum", value=10.0)
        if st.button("Classify fit", type="primary"):
            if hmin > hmax or smin > smax:
                st.error("Minimum dimensions must not exceed maximum dimensions.")
            else:
                low, high = hmin-smax, hmax-smin
                fit = "Clearance" if low > 0 else "Interference" if high < 0 else "Transition"
                st.metric("Fit classification", fit)
                st.write(f"Clearance interval: {low:.4f} to {high:.4f} {unit}")
                report_download({"fit": fit, "minimum_clearance": low,
                                 "maximum_clearance": high, "unit": unit}, "fit-analysis.json")
    st.caption("RSS assumes independent contributors. This simplified 1D model is not GD&T validation.")

elif page == "STL inspection":
    st.subheader("STL mesh inspection")
    unit = st.selectbox("Coordinate unit", ["Unknown", "mm", "cm", "m", "in"])
    upload = st.file_uploader("Upload STL", type=["stl"])
    if upload and st.button("Inspect mesh", type="primary"):
        try:
            result = parse_stl(upload.getvalue())
            result["coordinate_unit"] = unit
            a, b, c = st.columns(3)
            a.metric("Triangles", f"{result['triangles']:,}")
            b.metric("Degenerate", result["degenerate_triangles"])
            c.metric("Unit", unit)
            st.write("Bounding-box size:", result["size"], unit)
            st.json(result)
            report_download(result, "stl-inspection.json")
        except Exception as exc:
            st.error(f"STL inspection failed: {exc}")

elif page == "KiCad BOM":
    st.subheader("KiCad bill-of-materials review")
    upload = st.file_uploader("Upload BOM CSV", type=["csv"])
    if upload:
        try:
            rows = list(csv.DictReader(io.StringIO(upload.getvalue().decode("utf-8-sig"))))
            if not rows:
                st.warning("CSV contains no component rows.")
            else:
                keys = {k.lower().strip(): k for k in rows[0] if k}
                ref_key = next((keys[k] for k in ("reference", "refs", "ref", "designator") if k in keys), None)
                val_key = next((keys[k] for k in ("value", "value/part", "description") if k in keys), None)
                refs = [str(r.get(ref_key, "")).strip() for r in rows] if ref_key else []
                duplicates = sorted({r for r in refs if r and refs.count(r) > 1})
                missing = [i+2 for i, row in enumerate(rows)
                           if val_key and not str(row.get(val_key, "")).strip()]
                result = {"component_rows": len(rows), "reference_column": ref_key,
                          "value_column": val_key, "duplicate_references": duplicates,
                          "missing_value_rows": missing}
                a, b, c = st.columns(3)
                a.metric("Components", len(rows))
                b.metric("Duplicate refs", len(duplicates))
                c.metric("Missing values", len(missing))
                st.dataframe(rows, use_container_width=True, hide_index=True)
                report_download(result, "bom-review.json")
        except Exception as exc:
            st.error(f"BOM review failed: {exc}")

elif page == "Project integrity":
    st.subheader("Project ZIP integrity")
    upload = st.file_uploader("Upload project ZIP", type=["zip"])
    if upload and st.button("Inspect bundle", type="primary"):
        try:
            data = upload.getvalue()
            result = inspect_zip(data)
            result["archive_sha256"] = hashlib.sha256(data).hexdigest()
            if result["valid_zip"]:
                st.success("ZIP passed the path-safety check.")
            else:
                st.error("Unsafe archive paths detected.")
            a, b, c = st.columns(3)
            a.metric("Files", len(result["files"]))
            b.metric("Total bytes", f"{result['total_bytes']:,}")
            c.metric("Unsafe paths", len(result["unsafe_paths"]))
            st.dataframe(result["files"], use_container_width=True, hide_index=True)
            report_download(result, "project-integrity.json")
        except Exception as exc:
            st.error(f"Bundle inspection failed: {exc}")

st.divider()
st.caption("Hardware-Box · Apache-2.0 · Validate all results before design release.")
