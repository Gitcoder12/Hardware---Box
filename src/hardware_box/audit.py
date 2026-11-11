"""Repository-level quality audit for device records and asset manifests."""
from __future__ import annotations
import json
from pathlib import Path
from .validation import validate_device
from .assets import verify_manifest


def audit_project(root: str | Path, manifest: str | None = None) -> dict:
    base = Path(root).resolve()
    device_dir = base / 'database' / 'devices'
    records = []
    errors = []
    if device_dir.exists():
        for path in sorted(device_dir.glob('*.json')):
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                issues = validate_device(data)
                if issues:
                    errors.extend(f'{path.relative_to(base)}: {issue}' for issue in issues)
                else:
                    records.append(path.relative_to(base).as_posix())
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f'{path.relative_to(base)}: {exc}')
    else:
        errors.append('database/devices directory is missing')

    result = {'valid': not errors, 'device_records_checked': len(records), 'valid_records': records, 'errors': errors}
    if manifest:
        try:
            result['asset_integrity'] = verify_manifest(base, manifest)
            result['valid'] = result['valid'] and result['asset_integrity']['valid']
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            result['valid'] = False
            result['asset_integrity'] = {'valid': False, 'error': str(exc)}
    return result
