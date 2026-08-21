#!/usr/bin/env python3
"""Regression checks for the evidence-honest experimental macOS Intel CI corridor."""

from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GAME_LIBS_ROOT = Path(os.environ.get("OPENQ4_GAMELIBS_REPO", ROOT.parent / "openQ4-game")).resolve()


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def read_game(relative_path: str) -> str:
    path = GAME_LIBS_ROOT / relative_path
    if not path.is_file():
        raise AssertionError(f"openQ4-game file not found: {path}")
    return path.read_text(encoding="utf-8")


def require(source: str, needle: str, context: str) -> None:
    if needle not in source:
        raise AssertionError(f"Missing {needle!r} in {context}")


def reject(source: str, needle: str, context: str) -> None:
    if needle in source:
        raise AssertionError(f"Unexpected {needle!r} in {context}")


def validate_engine_corridor() -> None:
    meson = read("meson.build")
    validator = read("tools/validation/openq4_validate.py")
    dedicated = read("tools/tests/macos_dedicated_server_smoke.py")
    commit = read(".github/workflows/commit-validation.yml")
    push = read(".github/workflows/push-verification.yml")

    for token in (
        "if host_cpu_family == 'x86_64'",
        "binary_arch = 'x64'",
        "engine_client_binary_name = meson.project_name() + '-client_' + binary_arch",
        "engine_ded_binary_name = meson.project_name() + '-ded_' + binary_arch",
    ):
        require(meson, token, "openQ4 macOS x64 Meson naming")

    for token in (
        '"x64": frozenset(("x86_64",))',
        "validate_macos_binary_architectures(",
        "validate_macos_staged_metadata(",
    ):
        require(validator, token, "openQ4 staged x64 Mach-O validation")

    for token in (
        'if machine in {"x86_64", "amd64"}',
        'return "x64"',
        'f"openQ4-ded_{arch}"',
        'f"game-mp_{arch}.dylib"',
    ):
        require(dedicated, token, "macOS dedicated smoke Intel support")

    require(commit, "macos-x64:", "commit validation Intel job")
    intel_job = commit[commit.index("  macos-x64:") :]
    for token in (
        "macOS Intel x64 ${{ matrix.bridge_label }} Commit Validation",
        "runs-on: macos-15-intel",
        'MACOSX_DEPLOYMENT_TARGET: "11.0"',
        '"$(uname -m)" != "x86_64"',
        "macos_graphics_bridge: opengl",
        "macos_graphics_bridge: metal",
        "bash tools/validation/validate_pr.sh",
        "python tools/tests/macos_dedicated_server_smoke.py",
        "--arch x64",
        "commit-macos-x64-${{ matrix.artifact_suffix }}-payload",
        "commit-macos-x64-${{ matrix.artifact_suffix }}-dedicated-smoke",
    ):
        require(intel_job, token, "commit validation Intel corridor")

    for token in (
        "macOS Intel x64 OpenGL Push Verification",
        "macOS Intel x64 Metal Push Verification",
        "os: macos-15-intel",
        "artifact_name: macos-x64-opengl",
        "artifact_name: macos-x64-metal",
        'runtime_cases="renderer-default-safety-selftest"',
        "python tools/tests/macos_dedicated_server_smoke.py",
        "push-${{ matrix.artifact_name }}-dedicated-smoke",
    ):
        require(push, token, "push verification Intel corridor")


def validate_companion_corridor() -> None:
    workflow = read_game(".github/workflows/commit-validation.yml")
    meson = read_game("src/meson.build")
    contract = read_game("tools/tests/macos_meson_contract.py")
    readme = read_game("README.md")

    for token in (
        "['x86_64', 'aarch64'].contains(host_cpu_family)",
        "game_arch = 'x64'",
        "game_arch = 'arm64'",
        "'-Wl,-install_name,@loader_path/'",
    ):
        require(meson, token, "openQ4-game macOS architecture contract")

    for token in (
        "name: macOS ${{ matrix.arch_label }} GameLibs",
        "runner: macos-15",
        "runner: macos-15-intel",
        "module_arch: arm64",
        "module_arch: x64",
        "macho_arch: x86_64",
        'MACOSX_DEPLOYMENT_TARGET: "11.0"',
        "lipo -archs",
        "otool -D",
        "LC_BUILD_VERSION",
    ):
        require(workflow, token, "openQ4-game Intel CI corridor")

    require(contract, "runner: macos-15-intel", "openQ4-game Intel CI regression contract")
    require(readme, "experimental macOS ARM64 and Intel x64 coverage", "openQ4-game Intel CI documentation")
    require(readme, "Standalone Intel CI is build evidence only", "openQ4-game Intel support boundary")


def validate_policy_and_wiring() -> None:
    manual = read(".github/workflows/manual-release.yml")
    policy = read("docs/dev/macos-support-matrix-policy.md")
    building = read("BUILDING.md")
    platform = read("docs/dev/platform-support.md")
    plan = read("docs/dev/plan/2026-06-30-macos-compatibility-support.md")
    release_completion = read("docs/dev/release-completion.md")
    release_notes = read("docs/dev/releases/v0.8.1.md")
    validator = read("tools/validation/openq4_validate.py")
    commit = read(".github/workflows/commit-validation.yml")
    push = read(".github/workflows/push-verification.yml")

    for token in ("macos-x64", "macos-universal2", "macOS x64", "macOS universal2"):
        reject(manual, token, "manual release must remain arm64-only")

    for token in (
        "### Experimental Intel CI Corridor",
        "macos-15-intel",
        "hosted-runner reference",
        "experimental build/loader evidence only",
        "does not publish",
        "real Intel Apple hardware",
    ):
        require(policy, token, "macOS Intel matrix policy")

    require(building, "Hosted `macos-15-intel` jobs", "build documentation Intel corridor")
    require(platform, "Dedicated `macos-15-intel` engine and companion jobs", "platform support Intel corridor")

    for token in (
        "[x] Add a standard hosted Intel Mac runner",
        "[x] Add `../openQ4-game` macOS x86_64 CI",
        "[x] Add openQ4 macOS x86_64 staged-package validation",
        "[ ] Record clean hosted results",
        "[ ] Intel release expansion remains deferred",
    ):
        require(plan, token, "macOS compatibility Intel status")

    require(release_completion, "Experimental Intel macOS CI is now configured", "release completion Intel entry")
    require(release_notes, "experimental Intel x64 macOS CI", "curated release notes Intel entry")

    for source, context in (
        (validator, "local validation runner"),
        (commit, "commit validation workflow"),
        (push, "push verification workflow"),
    ):
        require(source, "macos_intel_ci.py", context)


def main() -> None:
    validate_engine_corridor()
    validate_companion_corridor()
    validate_policy_and_wiring()
    print("macos_intel_ci: ok")


if __name__ == "__main__":
    main()
