#!/usr/bin/env python3
"""Rebuild the official Hardware-Box v1.2.0 source archive from Git fragments."""
from __future__ import annotations

import hashlib
import io
import shutil
import sys
import tarfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
EXPECTED_SHA256 = "9b593b005ca911ec8e49f91dd229eafde3ad6ad16bb05a5f777d50a88767b7ad"


def extract_safely(data: bytes, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    base = destination.resolve()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:xz") as bundle:
        for member in bundle.getmembers():
            relative = PurePosixPath(member.name.replace("\\", "/"))
            parts = tuple(p for p in relative.parts if p not in ("", "."))
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
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                source = bundle.extractfile(member)
                if source is None:
                    raise ValueError(f"Could not read archive member: {member.name}")
                with source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)


def main() -> int:
    parts = sorted((ROOT / "source" / "parts").glob("*.bin"))
    if len(parts) != 14:
        raise SystemExit(f"Expected 14 source fragments, found {len(parts)}.")
    archive = b"".join(part.read_bytes() for part in parts)
    actual = hashlib.sha256(archive).hexdigest()
    if actual != EXPECTED_SHA256:
        raise SystemExit(f"SHA-256 mismatch: {actual}")
    destination = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else ROOT / "core-source"
    destination = destination.resolve()
    if destination == ROOT or ROOT in destination.parents:
        raise SystemExit("Choose an extraction directory outside the repository.")
    if destination.exists():
        shutil.rmtree(destination)
    extract_safely(archive, destination)
    print(f"Hardware-Box v1.2.0 restored to: {destination}")
    print(f"SHA-256 verified: {actual}")
    print("Install with: python -m pip install -e 'core-source[dev]'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
