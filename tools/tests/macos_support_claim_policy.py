#!/usr/bin/env python3
"""Regression checks for experimental macOS support-claim wording."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = "docs/dev/plans/2026-06-30-apple-support-no-macos-access.md"
HISTORICAL_ISSUE_73_RELEASES = {
    "v0.6.5.md",
    "v0.8.1.md",
    "v0.9.0.md",
    "v0.10.000.md",
}


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def require(haystack: str, needle: str, context: str) -> None:
    if needle not in haystack:
        raise AssertionError(f"Missing {needle!r} in {context}")


def require_any(haystack: str, needles: tuple[str, ...], context: str) -> None:
    if not any(needle in haystack for needle in needles):
        formatted = ", ".join(repr(needle) for needle in needles)
        raise AssertionError(f"Missing one of {formatted} in {context}")


def release_files() -> list[Path]:
    return sorted((ROOT / "docs" / "dev" / "releases").glob("v*.md"))


def validate_release_facing_docs() -> None:
    expected_tokens = {
        "README.md": (
            "experimental Apple Silicon/arm64 macOS",
            "OpenGL/Metal bridge packages",
        ),
        "BUILDING.md": (
            "Experimental manual macOS release artifacts are Apple Silicon/arm64 only",
            "Intel Mac and universal2 packages are not published",
            "Rosetta is not a supported release target",
            "Metal bridge",
            "comparison-only",
        ),
        "docs/user/getting-started.md": (
            "macOS support is experimental",
            "Apple Silicon/arm64 Macs on macOS 11 or later",
            "Intel Mac and universal2 packages are not published yet",
            "Rosetta is not a supported release target",
            "Metal bridge",
            "not a native Metal renderer",
        ),
        "docs/dev/platform-support.md": (
            "Current architecture policy: `arm64 only` for experimental Apple Silicon/arm64 release packages.",
            "Unsupported current macOS release targets: Intel Mac/`x86_64`, universal2 packages, and Rosetta",
            "Current package variants: `OpenGL` and `Metal bridge`",
            "not a native Metal renderer",
            "comparison-only diagnostics",
            "docs/dev/macos-signoff-evidence.md",
        ),
        "assets/release/README.html": (
            "experimental Apple Silicon/arm64 macOS",
            "macOS support is experimental",
            "Apple Silicon/arm64 Macs on macOS 11 or later",
            "Intel Mac and universal2 packages are not published yet",
            "Rosetta is not a supported release target",
            "Metal bridge",
            "not a native Metal renderer",
        ),
    }

    for relative_path, tokens in expected_tokens.items():
        source = read(relative_path)
        for token in tokens:
            require(source, token, relative_path)


def validate_release_completion_guard() -> None:
    release_completion = read("docs/dev/release-completion.md")

    for token in (
        "## macOS Support Claim Guard",
        'Release notes that mention macOS say "experimental Apple Silicon/arm64 macOS"',
        "Any first-class, stable, or fully supported macOS claim cites the current release entry",
        "docs/dev/macos-signoff-evidence.md",
        "Intel Mac, universal2, and Rosetta appear only as unsupported, not-published, or future-policy items",
        "`macos_graphics_bridge=metal` is described as a Metal bridge around the OpenGL renderer",
        "`platform_backend=native` on macOS is described as comparison-only diagnostic infrastructure",
        "GitHub issue #98 as the current visual-parity limitation",
        "closing the original issue #73 startup crash does not satisfy the macOS Evidence Gate",
    ):
        require(release_completion, token, "macOS support claim guard")


def validate_curated_release_notes() -> None:
    releases = release_files()
    if not releases:
        raise AssertionError("No curated release notes found under docs/dev/releases")

    promotion_phrases = (
        "first-class macos",
        "fully supported macos",
        "macos support is stable",
        "stable macos support",
        "production-ready macos",
        "macos support has graduated",
        "macos support is no longer experimental",
    )

    for release_path in releases:
        text = release_path.read_text(encoding="utf-8")
        if "macOS" not in text:
            continue

        context = release_path.relative_to(ROOT).as_posix()
        require(text, "experimental macOS", context)
        require(text, "Apple Silicon/arm64", context)
        require(text, "Intel Mac", context)
        require_any(text, ("not supported", "not published"), context)
        require(text, "Rosetta", context)
        require(text, "Metal bridge", context)
        require(text, "not a native Metal renderer", context)
        require(text, "platform_backend=native", context)
        require_any(text, ("comparison-only", "diagnostic infrastructure"), context)
        if release_path.name in HISTORICAL_ISSUE_73_RELEASES:
            require(text, "issue #73", f"{context} historical macOS limitation tracking")
        else:
            require(text, "issue #98", f"{context} current macOS limitation tracking")
        require(text, "docs/dev/macos-signoff-evidence.md", context)

        lowered = text.lower()
        for phrase in promotion_phrases:
            if phrase not in lowered:
                continue
            require(text, "docs/dev/macos-signoff-evidence.md", f"{context} promotion evidence")
            require(text, "macOS Evidence Gate", f"{context} promotion evidence gate")


def validate_phase0_plan_status() -> None:
    plan = read(PLAN_PATH)

    for token in (
        "## Phase 0: Keep The Support Claim Honest",
        '- [x] Keep `README.md`, `BUILDING.md`, `docs/user/getting-started.md`,',
        "- [x] Keep Intel Mac, universal2, and Rosetta out of user-facing claims until a",
        '- [x] Keep `macos_graphics_bridge=metal` wording as "Metal bridge" everywhere.',
        "- [x] Keep `platform_backend=native` documented as comparison-only.",
        "- [x] Add a docs/static guard that fails if release notes promote macOS beyond",
        "- [x] Add release-note boilerplate for issue #73 until it is closed or",
        "Phase 0 implementation status",
        "`tools/tests/macos_support_claim_policy.py`",
    ):
        require(plan, token, "Phase 0 Apple support plan")


def validate_ci_and_local_wiring() -> None:
    local_runner = read("tools/validation/openq4_validate.py")
    commit = read(".github/workflows/commit-validation.yml")
    push = read(".github/workflows/push-verification.yml")

    for source, context in (
        (local_runner, "local validation runner"),
        (commit, "commit validation workflow"),
        (push, "push verification workflow"),
    ):
        require(source, "macos_support_claim_policy.py", context)

    for source, context in (
        (commit, "commit validation workflow"),
        (push, "push verification workflow"),
    ):
        require(source, "python tools/tests/macos_support_claim_policy.py", context)


def main() -> None:
    validate_release_facing_docs()
    validate_release_completion_guard()
    validate_curated_release_notes()
    validate_phase0_plan_status()
    validate_ci_and_local_wiring()
    print("macos_support_claim_policy: ok")


if __name__ == "__main__":
    main()
