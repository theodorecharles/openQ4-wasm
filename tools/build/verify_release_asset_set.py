#!/usr/bin/env python3
"""Verify and record the exact file set approved for GitHub release upload."""

from __future__ import annotations

import argparse
import os
import re
import stat
import sys
from pathlib import Path


MAX_RELEASE_ASSETS = 64
SAFE_ASSET_NAME_RE = re.compile(r"openq4-[A-Za-z0-9][A-Za-z0-9._+-]{0,248}")


def _lstat(path: Path, label: str) -> os.stat_result:
    try:
        return path.lstat()
    except OSError as exc:
        raise RuntimeError(f"{label} is unavailable: {path}") from exc


def require_directory(path: Path, label: str) -> Path:
    path_stat = _lstat(path, label)
    if stat.S_ISLNK(path_stat.st_mode):
        raise RuntimeError(f"{label} must not be a symlink: {path}")
    if not stat.S_ISDIR(path_stat.st_mode):
        raise RuntimeError(f"{label} must be a directory: {path}")
    return path


def require_regular_file(path: Path, label: str) -> Path:
    path_stat = _lstat(path, label)
    if stat.S_ISLNK(path_stat.st_mode):
        raise RuntimeError(f"{label} must not be a symlink: {path}")
    if not stat.S_ISREG(path_stat.st_mode):
        raise RuntimeError(f"{label} must be a regular file: {path}")
    return path


def validate_asset_name(value: str) -> str:
    if (
        not value
        or SAFE_ASSET_NAME_RE.fullmatch(value) is None
        or ".." in value
        or "/" in value
        or "\\" in value
    ):
        raise RuntimeError(f"unsafe expected release artifact name: {value!r}")
    return value


def validate_expected_names(expected_names: list[str]) -> tuple[str, ...]:
    if not expected_names:
        raise RuntimeError("release artifact whitelist must not be empty")
    if len(expected_names) > MAX_RELEASE_ASSETS:
        raise RuntimeError(
            f"release artifact whitelist exceeds {MAX_RELEASE_ASSETS} entries"
        )

    validated = tuple(validate_asset_name(value) for value in expected_names)
    duplicates = sorted({value for value in validated if validated.count(value) > 1})
    if duplicates:
        raise RuntimeError(
            "release artifact whitelist contains duplicate names: "
            + ", ".join(duplicates)
        )
    return validated


def verify_asset_set(artifact_dir: Path, expected_names: list[str]) -> tuple[str, ...]:
    expected = validate_expected_names(expected_names)
    expected_set = set(expected)
    require_directory(artifact_dir, "release artifact directory")

    try:
        entries = list(os.scandir(artifact_dir))
    except OSError as exc:
        raise RuntimeError(
            f"release artifact directory could not be enumerated: {artifact_dir}"
        ) from exc

    actual_names: set[str] = set()
    invalid_entries: list[str] = []
    for entry in entries:
        try:
            is_regular = entry.is_file(follow_symlinks=False)
            is_symlink = entry.is_symlink()
        except OSError as exc:
            raise RuntimeError(f"release artifact changed during validation: {entry.name}") from exc
        if is_symlink or not is_regular:
            invalid_entries.append(entry.name)
            continue
        actual_names.add(entry.name)

    missing = sorted(expected_set - actual_names)
    unexpected = sorted(actual_names - expected_set)
    if missing or unexpected or invalid_entries:
        details: list[str] = []
        if missing:
            details.append("missing: " + ", ".join(repr(value) for value in missing))
        if unexpected:
            details.append(
                "unexpected: " + ", ".join(repr(value) for value in unexpected)
            )
        if invalid_entries:
            details.append(
                "non-regular: "
                + ", ".join(repr(value) for value in sorted(invalid_entries))
            )
        raise RuntimeError(
            "release artifact set does not match the exact approved whitelist ("
            + "; ".join(details)
            + ")"
        )

    for name in expected:
        require_regular_file(artifact_dir / name, f"approved release artifact {name}")
    return expected


def write_asset_manifest(output: Path, expected_names: tuple[str, ...]) -> None:
    require_directory(output.parent, "release asset manifest directory")
    if output.exists() or output.is_symlink():
        raise RuntimeError(f"release asset manifest output must not already exist: {output}")
    contents = "".join(f"{name}\n" for name in expected_names)
    try:
        with output.open("x", encoding="utf-8", newline="\n") as file_handle:
            file_handle.write(contents)
    except OSError as exc:
        raise RuntimeError(f"release asset manifest could not be written: {output}") from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--expected", required=True, action="append")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        expected = verify_asset_set(args.artifact_dir, args.expected)
        write_asset_manifest(args.manifest, expected)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(
        f"release artifact whitelist verified: {len(expected)} files; "
        f"manifest={args.manifest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
