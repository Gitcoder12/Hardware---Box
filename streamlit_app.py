"""Streamlit entry point for the packaged Hardware-Box v1.2.0 workbench."""
from __future__ import annotations

import hashlib
import io
import runpy
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

import streamlit as st

ROOT = Path(__file__).resolve().parent
EXPECTED_SHA256 = "9b593b005ca911ec8e49f91dd229eafde3ad6ad16bb05a5f777d50a88767b7ad"
CACHE = Path(tempfile.gettempdir()) / "hardware-box-core-1.2.0"


def safe_extract(archive: bytes, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    base = destination.resolve()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:xz") as bundle:
        for member in bundle.getmembers():
            relative = PurePosixPath(member.name.replace("\\", "/"))
            parts = tuple(part for part in relative.parts if part not in ("", "."))
            if relative.is_absolute() or ".." in parts:
                raise ValueError(f"Unsafe archive path: {member.name}")
            if not parts:
                continue
            if not (member.isdir() or member.isfile()):
                raise ValueError(f"Unsupported archive entry: {member.name}")
            target = base.joinpath(*parts)
            resolved = target.resolve()
            if resolved != base and base not in resolved.parents:
                raise ValueError(f"Archive path escapes destination: {member.name}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = bundle.extractfile(member)
            if source is None:
                raise ValueError(f"Could not read archive member: {member.name}")
            with source, target.open("wb") as output:
                shutil.copyfileobj(source, output)


def load_core() -> Path:
    marker = CACHE / ".source-sha256"
    app = CACHE / "hardware_box_streamlit.py"
    if marker.is_file() and marker.read_text(encoding="utf-8").strip() == EXPECTED_SHA256 and app.is_file():
        return CACHE

    parts_dir = ROOT / "source" / "parts"
    parts = sorted(parts_dir.glob("*.bin"))
    if len(parts) != 14:
        raise RuntimeError(f"Expected 14 source fragments; found {len(parts)}.")
    archive = b"".join(part.read_bytes() for part in parts)
    actual = hashlib.sha256(archive).hexdigest()
    if actual != EXPECTED_SHA256:
        raise RuntimeError(f"Core source checksum mismatch: expected {EXPECTED_SHA256}, got {actual}.")

    if CACHE.exists():
        shutil.rmtree(CACHE)
    CACHE.mkdir(parents=True)
    safe_extract(archive, CACHE)
    if not app.is_file():
        raise RuntimeError("The source bundle is missing hardware_box_streamlit.py.")
    marker.write_text(EXPECTED_SHA256 + "\n", encoding="utf-8")
    return CACHE


try:
    core = load_core()
    sys.path.insert(0, str(core))
    runpy.run_path(str(core / "hardware_box_streamlit.py"), run_name="__main__")
except Exception as exc:
    st.error(f"Hardware-Box could not start: {exc}")
    st.caption("Check the source-integrity and Streamlit smoke checks in GitHub Actions.")
    st.stop()
