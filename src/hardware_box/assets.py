"""Integrity manifests for hardware design assets.

The manifest records hashes and sizes; it does not prove ownership, safety, or
manufacturability. Paths are relative to the selected project root.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

MANIFEST_VERSION = 1
DEFAULT_EXCLUDES = {'.git', '.venv', '__pycache__', '.hardware-box', 'build', 'dist'}

def _excluded(relative: Path) -> bool:
    return any(part in DEFAULT_EXCLUDES or part.endswith('.egg-info') for part in relative.parts)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b''):
            digest.update(chunk)
    return digest.hexdigest()


def create_manifest(root: str | Path, output: str | Path = 'hardware-box-manifest.json') -> dict:
    """Create a deterministic asset inventory with SHA-256 hashes."""
    base = Path(root).resolve()
    if not base.is_dir():
        raise NotADirectoryError(base)
    output_path = Path(output)
    output_resolved = output_path.resolve() if output_path.is_absolute() else (base / output_path).resolve()
    entries = []
    for path in sorted(base.rglob('*')):
        if _excluded(path.relative_to(base)):
            continue
        if path.is_symlink():
            raise ValueError(f'Symlinks are not allowed in asset manifests: {path.relative_to(base)}')
        if not path.is_file() or path.resolve() == output_resolved:
            continue
        rel = path.relative_to(base).as_posix()
        entries.append({'path': rel, 'size_bytes': path.stat().st_size, 'sha256': sha256_file(path)})
    return {
        'manifest_version': MANIFEST_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'algorithm': 'sha256',
        'assets': entries,
    }


def write_manifest(root: str | Path, output: str | Path = 'hardware-box-manifest.json') -> Path:
    base = Path(root).resolve()
    target = Path(output)
    if not target.is_absolute():
        target = base / target
    manifest = create_manifest(base, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return target


def verify_manifest(root: str | Path, manifest_path: str | Path = 'hardware-box-manifest.json') -> dict:
    """Verify every listed file and report missing, modified and extra files."""
    base = Path(root).resolve()
    source = Path(manifest_path)
    if not source.is_absolute():
        source = base / source
    manifest = json.loads(source.read_text(encoding='utf-8'))
    if manifest.get('manifest_version') != MANIFEST_VERSION or manifest.get('algorithm') != 'sha256':
        raise ValueError('Unsupported asset manifest version or hash algorithm')
    assets = manifest.get('assets')
    if not isinstance(assets, list):
        raise ValueError('Manifest assets must be an array')

    seen = set()
    missing, modified = [], []
    for item in assets:
        if not isinstance(item, dict) or not isinstance(item.get('path'), str):
            raise ValueError('Each manifest asset must contain a relative path')
        rel = PurePosixPath(item['path'])
        if rel.is_absolute() or '..' in rel.parts or not rel.parts:
            raise ValueError(f'Unsafe manifest path: {item["path"]}')
        if item['path'] in seen:
            raise ValueError(f'Duplicate manifest path: {item["path"]}')
        seen.add(item['path'])
        unresolved = base / Path(*rel.parts)
        if unresolved.is_symlink():
            raise ValueError(f'Symlink asset paths are not allowed: {item["path"]}')
        candidate = unresolved.resolve()
        if base not in candidate.parents:
            raise ValueError(f'Asset escapes project root: {item["path"]}')
        if not candidate.is_file() or candidate.is_symlink():
            missing.append(item['path'])
            continue
        if candidate.stat().st_size != item.get('size_bytes') or sha256_file(candidate) != item.get('sha256'):
            modified.append(item['path'])

    actual = set()
    for path in base.rglob('*'):
        if _excluded(path.relative_to(base)):
            continue
        if path.is_file() and not path.is_symlink() and path.resolve() != source.resolve():
            actual.add(path.relative_to(base).as_posix())
    extra = sorted(actual - seen)
    return {
        'valid': not missing and not modified and not extra,
        'listed': len(seen),
        'missing': sorted(missing),
        'modified': sorted(modified),
        'untracked': extra,
    }
