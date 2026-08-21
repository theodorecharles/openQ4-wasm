#!/usr/bin/env python3
"""Static checks for the experimental macOS OpenAL provider policy."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = "docs/dev/plans/2026-06-30-apple-support-no-macos-access.md"


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def require(haystack: str, needle: str, context: str) -> None:
    if needle not in haystack:
        raise AssertionError(f"Missing {needle!r} in {context}")


def reject(haystack: str, needle: str, context: str) -> None:
    if needle in haystack:
        raise AssertionError(f"Unexpected {needle!r} in {context}")


def reject_regex(haystack: str, pattern: str, context: str) -> None:
    if re.search(pattern, haystack, flags=re.IGNORECASE | re.DOTALL):
        raise AssertionError(f"Unexpected pattern {pattern!r} in {context}")


def validate_meson_provider_switch() -> None:
    options = read("meson_options.txt")
    meson = read("meson.build")

    for token in (
        "'macos_openal_provider'",
        "choices: ['apple_framework', 'system']",
        "value: 'apple_framework'",
        "apple_framework is the release default",
        "system requires a pkg-config OpenAL Soft dependency plus OpenAL Soft-style AL/... headers for migration testing",
    ):
        require(options, token, "macOS OpenAL provider Meson option")

    for token in (
        "if host_system != 'darwin' and macos_openal_provider != 'apple_framework'",
        "macos_openal_provider=' + macos_openal_provider + ' is only valid on macOS hosts.",
        "if macos_openal_provider == 'apple_framework'",
        "dependency('appleframeworks', modules: ['OpenAL'], required: true)",
        "dependency('openal', required: true, method: 'pkg-config')",
        "if macos_openal_provider == 'system'",
        "-DUSE_OPENAL_SOFT_INCLUDES=1",
        "'macOS OpenAL provider': macos_openal_provider",
    ):
        require(meson, token, "macOS OpenAL provider Meson wiring")

    reject(
        meson,
        "openal_dep = dependency('openal', required: true)\n",
        "macOS system OpenAL provider must not fall back to Apple's framework",
    )


def validate_release_workflow_pin() -> None:
    manual_release = read(".github/workflows/manual-release.yml")
    commit = read(".github/workflows/commit-validation.yml")
    push = read(".github/workflows/push-verification.yml")

    for source, context in (
        (manual_release, "manual release workflow"),
        (commit, "commit validation workflow"),
        (push, "push verification workflow"),
    ):
        require(source, "macos_openal_provider", context)
        require(source, "apple_framework", context)
        reject_regex(
            source,
            r"(platform|name|label)[^\n]*(macos|macOS).*?macos_openal_provider:\s*system",
            context,
        )
        reject_regex(
            source,
            r'"platform":\s*"macos".*?"macos_openal_provider":\s*"system"',
            context,
        )

    require(manual_release, '"macos_openal_provider": "apple_framework"', "manual release macOS matrix")
    require(commit, "macos_openal_provider: apple_framework", "commit validation macOS matrix")
    require(push, "macos_openal_provider: apple_framework", "push verification macOS matrix")


def validate_policy_docs() -> None:
    policy = read("docs/dev/macos-openal-provider-policy.md")
    building = read("BUILDING.md")
    platform = read("docs/dev/platform-support.md")
    workflow_doc = read("docs/dev/macos-vm-testing-workflow.md")

    for token in (
        "# macOS OpenAL Provider Policy",
        "-Dmacos_openal_provider=apple_framework",
        "Apple's OpenAL framework",
        "not bundled OpenAL Soft",
        "`-Dmacos_openal_provider=system` is migration-only",
        "pkg-config-only",
        "PKG_CONFIG_PATH",
        "Library location",
        "openQ4.app/Contents/Frameworks/",
        "Install names",
        "@executable_path/../Frameworks/",
        "Codesigning",
        "License notice",
        "Notarization allowlist",
        ".dSYM",
        "case-fold collisions",
        "OpenAL vendor:",
        "OpenAL renderer:",
        "OpenAL active device:",
        "OpenAL EFX",
        "logs/openal-summary.txt",
        "must not launch openQ4",
    ):
        require(policy, token, "macOS OpenAL provider policy doc")

    for source, context in (
        (building, "build documentation"),
        (platform, "platform support documentation"),
        (workflow_doc, "macOS workflow documentation"),
    ):
        require(source, "apple_framework", context)
        require(source, "migration", context)
        require(source, "OpenAL Soft", context)
        require(source, "docs/dev/macos-openal-provider-policy.md", context)

    require(building, "current macOS packages do not bundle OpenAL Soft", "build documentation")
    require(
        building,
        "dependency('openal', method: 'pkg-config')",
        "build documentation pkg-config dependency",
    )
    reject(
        building,
        "with `dependency('openal')`",
        "build documentation generic OpenAL dependency",
    )
    require(platform, "current macOS packages do not bundle OpenAL Soft", "platform support documentation")
    require(workflow_doc, "not release evidence that macOS packages bundle OpenAL Soft", "macOS workflow documentation")


def validate_user_facing_docs_do_not_overclaim_openal_soft() -> None:
    user_docs = {
        "README": read("README.md"),
        "getting started": read("docs/user/getting-started.md"),
        "package README": read("assets/release/README.html"),
        "release notes": read("docs/dev/releases/v0.6.5.md"),
    }

    forbidden_patterns = (
        r"macOS[^.\n]*(bundles?|ships?|includes?)[^.\n]*OpenAL Soft",
        r"OpenAL Soft[^.\n]*(bundled|included|shipped)[^.\n]*macOS",
        r"macOS[^.\n]*OpenAL Soft provider",
    )
    for context, source in user_docs.items():
        for pattern in forbidden_patterns:
            reject_regex(source, pattern, context)


def validate_support_intake_audio_fields() -> None:
    template = read(".github/ISSUE_TEMPLATE/macos-crash-report.yml")
    collector = read("tools/macos/collect_macos_support_info.sh")
    support_doc = read("docs/user/macos-support-data.md")

    for token in (
        "id: openal_vendor",
        "label: OpenAL vendor",
        "OpenAL vendor:",
        "id: openal_renderer",
        "label: OpenAL renderer",
        "OpenAL renderer:",
        "id: openal_device",
        "label: OpenAL device name",
        "OpenAL active device:",
        "id: openal_efx_lines",
        "label: OpenAL EFX warnings",
        "OpenAL EFX",
        "logs/openal-summary.txt",
    ):
        require(template, token, "macOS crash issue template OpenAL fields")

    for token in (
        "logs/openal-summary.txt",
        "OpenAL vendor, OpenAL renderer, OpenAL version, OpenAL requested device, OpenAL default device, OpenAL active device, OpenAL EFX",
        "grep -E 'OpenAL (vendor|renderer|version|requested device|default device|active device|ALC version|EFX|HRTF|output mode)",
        "OpenAL vendor, renderer, device name, and EFX warning lines could not be copied without launching openQ4.",
        "logs/openal-summary.txt records OpenAL vendor, renderer, version, device, and EFX warning/status lines",
    ):
        require(collector, token, "macOS support collector OpenAL summary")

    for token in (
        "OpenAL audio lines",
        "`OpenAL vendor:`",
        "`OpenAL renderer:`",
        "`OpenAL active device:`",
        "`OpenAL EFX ...`",
        "`logs/openal-summary.txt`",
        "without launching openQ4",
    ):
        require(support_doc, token, "macOS support-data guide OpenAL fields")


def validate_plan_release_notes_and_wiring() -> None:
    plan = read(PLAN_PATH)
    release_completion = read("docs/dev/release-completion.md")
    release_notes = read("docs/dev/releases/v0.6.5.md")
    local_runner = read("tools/validation/openq4_validate.py")
    commit = read(".github/workflows/commit-validation.yml")
    push = read(".github/workflows/push-verification.yml")
    macos_debug = read(".github/workflows/macos-debug.yml")

    for token in (
        "- [x] Keep release builds pinned to `macos_openal_provider=apple_framework`",
        "- [x] Write a static package policy for a future OpenAL Soft macOS provider:",
        "- [x] Keep `-Dmacos_openal_provider=system` described as migration-only.",
        "- [x] Add static tests that user-facing release docs do not imply OpenAL Soft is",
        "- [x] Add crash/support template fields for OpenAL vendor, renderer, device",
        "Phase 6 implementation status",
        "docs/dev/macos-openal-provider-policy.md",
        "tools/tests/macos_openal_provider_policy.py",
        "No macOS platform testing is required or claimed for Phase 6.",
    ):
        require(plan, token, "Phase 6 Apple support plan")

    for source, context in (
        (release_completion, "release completion notes"),
        (release_notes, "curated release notes"),
    ):
        require(source, "Apple OpenAL framework", context)
        require(source, "OpenAL Soft", context)
        require(source, "logs/openal-summary.txt", context)

    for source, context in (
        (local_runner, "local validation runner"),
        (commit, "commit validation workflow"),
        (push, "push verification workflow"),
        (macos_debug, "macOS debug workflow"),
    ):
        require(source, "macos_openal_provider_policy.py", context)

    for source, context in (
        (commit, "commit validation workflow"),
        (push, "push verification workflow"),
        (macos_debug, "macOS debug workflow"),
    ):
        require(source, "python tools/tests/macos_openal_provider_policy.py", context)


def main() -> None:
    validate_meson_provider_switch()
    validate_release_workflow_pin()
    validate_policy_docs()
    validate_user_facing_docs_do_not_overclaim_openal_soft()
    validate_support_intake_audio_fields()
    validate_plan_release_notes_and_wiring()
    print("macos_openal_provider_policy: ok")


if __name__ == "__main__":
    main()
