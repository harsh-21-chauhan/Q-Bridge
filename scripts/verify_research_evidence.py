#!/usr/bin/env python3
"""Verify canonical evidence and optionally restore original JSON/CSV artifacts.

Uses the standard library only. Restoration requires a new destination and
preserves original bytes, including quick-run prefixes of full trial files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
from zipfile import BadZipFile, ZipFile


ROOT = Path(__file__).resolve().parents[1]


def safe_relative(value: str) -> str:
    """Keep manifest paths beneath the repository/restoration directory."""
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        raise ValueError(f"Unsafe evidence path: {value!r}")
    return value


def check_content(data: bytes, record: dict, label: str) -> None:
    if len(data) != record["bytes"]:
        raise ValueError(f"Size mismatch: {label}")
    if hashlib.sha256(data).hexdigest() != record["sha256"]:
        raise ValueError(f"SHA-256 mismatch: {label}")


def verify() -> tuple[dict[str, bytes], int, int]:
    manifest = json.loads((ROOT / "research/provenance.json").read_text())
    if manifest["schema_version"] != 1:
        raise ValueError("Unsupported provenance schema")
    archive_data: dict[str, dict[str, bytes]] = {}
    for archive in manifest["archives"]:
        name = safe_relative(archive["path"])
        if name in archive_data:
            raise ValueError(f"Repeated archive: {name}")
        path = ROOT / name
        check_content(path.read_bytes(), archive, name)
        with ZipFile(path) as handle:
            names = handle.namelist()
            if len(names) != len(set(names)) or len(names) != archive["members"]:
                raise ValueError(f"Unexpected or repeated archive members: {name}")
            if handle.testzip() is not None:
                raise ValueError(f"Invalid archive CRC: {name}")
            archive_data[name] = {
                safe_relative(member): handle.read(member) for member in names
            }

    artifacts = {}
    for artifact in manifest["artifacts"]:
        name = safe_relative(artifact["original_path"])
        if name in artifacts:
            raise ValueError(f"Repeated original artifact: {name}")
        artifacts[name] = artifact
    restored: dict[str, bytes] = {}
    resolving: set[str] = set()
    used_members: set[tuple[str, str]] = set()
    canonical_hashes: dict[str, str] = {}
    direct_files: set[str] = set()

    def resolve(name: str) -> bytes:
        if name in restored:
            return restored[name]
        if name in resolving:
            raise ValueError(f"Cyclic prefix reference: {name}")
        resolving.add(name)
        artifact = artifacts[name]
        location = artifact["storage"]
        if "prefix_of" in location:
            original = resolve(location["prefix_of"])
            size = location["bytes"]
            if not 0 <= size <= len(original):
                raise ValueError(f"Invalid prefix size: {name}")
            content = original[:size]
        elif "archive" in location:
            key = (location["archive"], location["member"])
            if key in used_members:
                raise ValueError(f"Repeated canonical member: {key}")
            used_members.add(key)
            content = archive_data[key[0]][key[1]]
        else:
            path = safe_relative(location["file"])
            if path in direct_files:
                raise ValueError(f"Repeated canonical file: {path}")
            direct_files.add(path)
            content = (ROOT / path).read_bytes()
        check_content(content, artifact, name)
        if "prefix_of" not in location:
            digest = artifact["sha256"]
            if digest in canonical_hashes:
                raise ValueError(f"Duplicate contents: {name}, {canonical_hashes[digest]}")
            canonical_hashes[digest] = name
        restored[name] = content
        resolving.remove(name)
        return content

    for name in artifacts:
        resolve(name)
    expected_members = {
        (archive, member)
        for archive, members in archive_data.items()
        for member in members
    }
    if used_members != expected_members:
        raise ValueError("Archive member coverage differs from the manifest")
    expected_files = set(archive_data) | direct_files
    actual_files = {
        path.relative_to(ROOT).as_posix()
        for folder in ("evidence", "summaries", "examples")
        for path in (ROOT / "research" / folder).rglob("*")
        if path.is_file() and path.name != ".DS_Store"
    }
    if actual_files != expected_files:
        raise ValueError(f"Unexpected/missing evidence files: {sorted(actual_files ^ expected_files)}")
    return restored, len(canonical_hashes), len(archive_data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restore-dir", type=Path,
                        help="Reconstruct original JSON/CSV paths under a new directory")
    args = parser.parse_args()
    try:
        if args.restore_dir is not None and args.restore_dir.exists():
            raise ValueError("Restoration destination already exists; choose a new directory")
        artifacts, unique_count, archive_count = verify()
        print(f"Verified {archive_count} archives, {unique_count} unique records, "
              f"and {len(artifacts)} recoverable original artifacts.")
        if args.restore_dir is not None:
            args.restore_dir.mkdir(parents=True, exist_ok=False)
            for name, content in artifacts.items():
                target = args.restore_dir / safe_relative(name)
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as handle:
                    handle.write(content)
            print(f"Restored original paths under {args.restore_dir.resolve()}")
        return 0
    except (OSError, ValueError, KeyError, BadZipFile) as exc:
        print(f"Evidence verification failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
