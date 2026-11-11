"""Portable, integrity-checked project bundles with path traversal protection."""
from __future__ import annotations
import hashlib, json, os, shutil, stat, zipfile
from pathlib import Path, PurePosixPath
from typing import Any

BUNDLE_NAME = "HARDWARE-BOX-BUNDLE.json"
BUNDLE_VERSION = 1
EXCLUDED_PARTS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".hardware-box", "build", "dist", "node_modules"}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_stream(stream) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    while True:
        chunk = stream.read(1024 * 1024)
        if not chunk:
            break
        digest.update(chunk)
        size += len(chunk)
    return digest.hexdigest(), size


def _safe_rel(name: str) -> PurePosixPath:
    rel = PurePosixPath(name)
    if rel.is_absolute() or not rel.parts or any(p in {"..", ""} for p in rel.parts) or "\\" in name:
        raise ValueError(f"Unsafe archive path: {name!r}")
    return rel


def create_bundle(root: str | Path, destination: str | Path) -> dict[str, Any]:
    base = Path(root).resolve(); output = Path(destination).resolve()
    if not base.is_dir(): raise NotADirectoryError(base)
    if output == base or base in output.parents: raise ValueError("Bundle destination must be outside the project root")
    assets = []
    for path in sorted(base.rglob("*")):
        rel = path.relative_to(base)
        if any(part in EXCLUDED_PARTS or part.endswith(".egg-info") for part in rel.parts) or path.is_symlink() or not path.is_file():
            continue
        if path.resolve() == output: continue
        with path.open("rb") as stream:
            digest, size = _sha256_stream(stream)
        assets.append({"path": rel.as_posix(), "size_bytes": size, "sha256": digest})
    manifest = {"bundle_version": BUNDLE_VERSION, "tool": "Hardware-Box", "file_count": len(assets), "assets": assets}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr(BUNDLE_NAME, json.dumps(manifest, indent=2, sort_keys=True))
        for item in assets:
            archive.write(base / Path(*PurePosixPath(item["path"]).parts), item["path"])
    return {"bundle": str(output), "file_count": len(assets), "size_bytes": output.stat().st_size}


def verify_bundle(bundle: str | Path) -> dict[str, Any]:
    path = Path(bundle)
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)): raise ValueError("Bundle contains duplicate archive paths")
        if BUNDLE_NAME not in names: raise ValueError(f"Missing {BUNDLE_NAME}")
        for info in archive.infolist():
            _safe_rel(info.filename)
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode): raise ValueError(f"Symlink entry is not allowed: {info.filename}")
        try: manifest = json.loads(archive.read(BUNDLE_NAME))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc: raise ValueError("Invalid bundle manifest") from exc
        if manifest.get("bundle_version") != BUNDLE_VERSION or not isinstance(manifest.get("assets"), list):
            raise ValueError("Unsupported or malformed bundle manifest")
        if manifest.get("file_count") != len(manifest["assets"]):
            raise ValueError("Bundle manifest file_count does not match assets array")
        expected = {}
        for item in manifest["assets"]:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str): raise ValueError("Malformed asset entry")
            rel = _safe_rel(item["path"])
            name = rel.as_posix()
            if name == BUNDLE_NAME or name in expected: raise ValueError(f"Duplicate/reserved manifest path: {name}")
            expected[name] = item
        actual = set(names) - {BUNDLE_NAME}
        missing, modified, untracked = sorted(set(expected) - actual), [], sorted(actual - set(expected))
        for name in sorted(set(expected) & actual):
            item = expected[name]
            with archive.open(name, "r") as stream:
                digest, size = _sha256_stream(stream)
            if size != item.get("size_bytes") or digest != item.get("sha256"):
                modified.append(name)
        valid = not missing and not modified and not untracked
        return {"valid": valid, "file_count": len(expected), "missing": missing,
                "modified": modified, "untracked": untracked, "bundle": str(path)}


def extract_bundle(bundle: str | Path, destination: str | Path, overwrite: bool = False) -> dict[str, Any]:
    result = verify_bundle(bundle)
    if not result["valid"]: raise ValueError(f"Bundle integrity check failed: {result}")
    target = Path(destination).resolve()
    target.mkdir(parents=True, exist_ok=True)
    written = 0
    with zipfile.ZipFile(bundle, "r") as archive:
        for name in archive.namelist():
            if name == BUNDLE_NAME: continue
            rel = _safe_rel(name)
            dest = (target / Path(*rel.parts)).resolve()
            if target != dest and target not in dest.parents: raise ValueError(f"Extraction path escapes destination: {name}")
            if dest.exists() and not overwrite: raise FileExistsError(dest)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name, "r") as source, dest.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            written += 1
    return {"destination": str(target), "files_extracted": written, "verified_before_extract": True}
