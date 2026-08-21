#!/usr/bin/env python3
"""Regression checks for Linux packaging and audit-status guidance."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def require(haystack: str, needle: str, context: str) -> None:
    if needle not in haystack:
        raise AssertionError(f"Missing {needle!r} in {context}")


def validate_building_packager_notes() -> None:
    source = read("BUILDING.md")

    require(source, "### Linux Packager Notes", "BUILDING Linux packager section")
    require(source, "Meson 1.6.0 or newer", "BUILDING Meson floor")
    require(source, "SDL3 `>=3.4.4`", "BUILDING SDL3 floor")
    require(source, "libopengl-dev", "BUILDING native OpenGL development dependency")
    require(source, "Ubuntu 24.04-class userspace", "BUILDING Linux userspace floor")
    require(source, "SDL_VIDEODRIVER=wayland", "BUILDING Wayland driver toggle")
    require(source, "SDL_VIDEO_DRIVER=wayland", "BUILDING Wayland driver toggle")
    require(source, "SDL_VIDEODRIVER=x11", "BUILDING X11 driver toggle")
    require(source, "SDL_VIDEO_DRIVER=x11", "BUILDING X11 driver toggle")
    require(source, "OPENQ4_FORCE_X11=1", "BUILDING project XWayland fallback")
    require(source, "OPENQ4_WAYLAND_DISABLE_LIBDECOR=1", "BUILDING libdecor opt-out")
    require(source, "OPENQ4_WAYLAND_PREFER_LIBDECOR=1", "BUILDING libdecor preference")
    require(source, "OPENQ4_WAYLAND_SYNC_WINDOW_OPS=1", "BUILDING sync window diagnostics")
    require(source, "openq4-<version>-linux-<arch>-debugsymbols.tar.xz", "BUILDING Linux debug symbols")
    require(source, "OPENQ4_GAMELIBS_REPO", "BUILDING GameLibs source-input path")
    require(source, "openq4_gamelibs_stage_manifest.json", "BUILDING GameLibs staging manifest")
    require(source, "validate_push.sh --install", "BUILDING package validation command")
    require(source, "validate_pr.sh --runtime", "BUILDING runtime validation command")
    require(source, "docs/dev/linux-arm64-cross-compilation.md", "BUILDING ARM64 cross-build guidance")


def validate_platform_support() -> None:
    source = read("docs/dev/platform-support.md")

    require(source, "Linux packaged compatibility floor", "platform support Linux floor")
    require(source, "Ubuntu 24.04", "platform support Linux floor")
    require(source, "desktop OpenGL plus EGL/Wayland or X11/GLX", "platform support display stack")
    require(source, "Linux ARM64 currently means", "platform support ARM64 graphics boundary")
    require(source, "OPENQ4_FORCE_X11=1", "platform support XWayland fallback")
    require(source, "OPENQ4_WAYLAND_DISABLE_LIBDECOR=1", "platform support libdecor fallback")


def validate_plan_status() -> None:
    source = read("docs/dev/plans/2026-06-20-linux.md")

    require(source, "## Implementation status (June 20, 2026)", "Linux audit status appendix")
    require(source, "Native Wayland runtime CI", "Linux audit status appendix")
    require(source, "Linux hardening", "Linux audit status appendix")
    require(source, "openQ4-game source-input contract", "Linux audit status appendix")
    require(source, "Linux sanitizer build lane", "Linux audit status appendix")
    require(source, "Downstream Linux packager guidance", "Linux audit status appendix")
    require(source, "Still outstanding", "Linux audit outstanding list")
    require(source, "real Linux hardware and compositor families", "Linux audit outstanding list")
    require(source, "libFuzzer or AFL++", "Linux audit outstanding list")


def validate_ci_wiring() -> None:
    commit = read(".github/workflows/commit-validation.yml")
    push = read(".github/workflows/push-verification.yml")
    runner = read("tools/validation/openq4_validate.py")

    for source, context in ((commit, "commit script smoke"), (push, "push script smoke")):
        require(source, "tools/tests/linux_packaging_guidance.py", context)
        require(source, "python tools/tests/linux_packaging_guidance.py", context)

    require(runner, "linux_packaging_guidance.py", "validation runner")


def validate_release_note() -> None:
    source = read("docs/dev/release-completion.md")

    require(source, "Linux packager guidance is clearer", "release completion notes")
    require(source, "SDL3 floor", "release completion notes")
    require(source, "debug-symbol archive", "release completion notes")


def main() -> None:
    validate_building_packager_notes()
    validate_platform_support()
    validate_plan_status()
    validate_ci_wiring()
    validate_release_note()
    print("linux_packaging_guidance: ok")


if __name__ == "__main__":
    main()
