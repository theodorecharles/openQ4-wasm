# macOS Support Matrix Policy

Updated: 2026-07-15

This document defines the current macOS architecture and OS-version matrix for
openQ4 releases. It records what is supported now, what is deliberately not
claimed, and what evidence is required before the matrix can expand.

## Current Release Matrix

Current macOS release artifacts are experimental Apple Silicon/arm64 only:

- `openq4-<version>-macos-arm64-opengl.dmg`
- `openq4-<version>-macos-arm64-metal.dmg`
- `openq4-<version>-macos-arm64-opengl-unsigned.tar.gz` for experimental fallback output
- `openq4-<version>-macos-arm64-metal-unsigned.tar.gz` for experimental fallback output

The current arm64 CI and manual release lanes use GitHub-hosted `macos-15`
runners for configure, build, staging, package, signing, notarization, and
static validation. Push jobs also require an assetless renderer launch for the
OpenGL and Metal bridge variants, and release jobs launch the packaged app
executable from a Finder-style unrelated working directory. Hosted runner
success is not a replacement for real Apple-hardware gameplay signoff.

## Architecture Policy

The current user-facing release policy is `arm64 only`. Experimental Intel
build validation does not expand that release promise.

Not supported by current user-facing macOS releases:

- Intel Mac / `x86_64` packages.
- universal2 packages.
- Rosetta as a supported compatibility layer.

Local or hosted x86_64 experiments and Rosetta experiments may be useful for
development, but they do not change the published support matrix. User-facing
docs and release notes must continue to say Apple Silicon/arm64 only until the
requirements below are met.

### Experimental Intel CI Corridor

GitHub currently provides the standard x86_64 `macos-15-intel` runner documented
in its [hosted-runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
openQ4 commit and push validation now configure thin Intel builds for both the
OpenGL and Metal bridge variants, stage and architecture-check the client,
dedicated server, and SP/MP dylibs, run the assetless renderer safety probe, and
require the assetless dedicated server to initialize the staged MP module and
shut down cleanly. `openQ4-game` has a matching standalone x64 job that verifies
both module slices, install names, and the macOS 11 deployment floor.

This corridor is experimental build/loader evidence only. It does not publish
`macos-x64` downloads, claim Rosetta compatibility, or replace stock-asset SP,
MP, audio, input, display, package, signing, notarization, and Gatekeeper tests
on real Intel Apple hardware. Passing hosted results must be recorded before
even the CI corridor is described as proven rather than configured.

The hosted `macos-universal2` commit gate now merges matched thin artifacts for
both bridge variants, checks the exact two-slice set, package-relative module
IDs, per-slice dependencies/deployment metadata, dSYM UUID records, and a
native assetless dedicated-server lifecycle. It remains pre-publication build
evidence only: the single-download merge contract and remaining real-hardware
signoff boundary are defined in `docs/dev/macos-universal2-design.md`.

Before claiming Intel Mac or universal2 support, openQ4 must have:

- An explicit release-lane decision: separate `macos-x64` artifacts or
  universal2 artifacts.
- Passing matching openQ4 and `openQ4-game` CI coverage for every claimed architecture.
- `lipo -archs` validation for the app executable, loose client, dedicated
  server, and both SP/MP game dylibs.
- `otool -L` and install-name validation after any `lipo` combine step.
- Developer ID signing, notarization, stapling, `spctl`, and `hdiutil`
  validation after final artifact creation.
- Real Apple-hardware runtime signoff on every claimed architecture.
- Artifact names and docs that distinguish `macos-arm64`, `macos-x64`, and
  `macos-universal2` when more than one architecture is published.

## OS-Version Policy

The current packaged compatibility floor is `macOS 11` for the experimental
Apple Silicon/arm64 release line. Meson sets `-mmacosx-version-min=11.0`, app
metadata sets `LSMinimumSystemVersion` to `11.0`, and user-facing docs say
macOS 11 or later. The Bash Meson wrapper now supplies
`MACOSX_DEPLOYMENT_TARGET=11.0` when it is unset so vendored dependencies and
companion GameLibs inherit the same floor; an explicit dotted override remains
available for deliberate local compatibility experiments.

The validation policy is:

- Treat `macOS 11` as a documented floor, not as proven first-class support,
  until floor-version signoff exists on Apple Silicon hardware or a compliant
  Apple-hardware VM.
- Treat the latest public macOS release as the rolling current-version signoff
  target for every release that changes platform, packaging, input, audio,
  renderer, loader, or game-module behavior.
- Record both floor-version and latest-version results before promoting macOS
  beyond experimental.
- Keep the published OS range no broader than the evidence in
  `docs/dev/macos-signoff-evidence.md`.

Before changing the floor, update all of these together:

- Meson deployment target.
- `tools/build/package_nightly.py` app metadata.
- `.github/workflows/manual-release.yml` package validation.
- `BUILDING.md`.
- `docs/dev/platform-support.md`.
- `docs/user/getting-started.md`.
- `assets/release/README.html`.
- `docs/dev/macos-signoff-evidence.md`.
- macOS matrix and package policy tests.

## Bundled MoltenVK And The OS Floor

Added: 2026-07-25.

Both macOS package variants now also carry the Vulkan renderer module
(`renderer-vk_<arch>.dylib`) and MoltenVK, a Vulkan-on-Metal translation layer
(`libMoltenVK.dylib`), inside `openQ4.app/Contents/Frameworks`. This adds no
package variant, no artifact name, and no architecture to the matrix above:
OpenGL remains the default renderer and Vulkan is opt-in through
`r_renderApi vulkan`. The decision plan is
[macos-moltenvk-decision.md](macos-moltenvk-decision.md).

The matrix consequence is the OS floor. MoltenVK is pinned to `v1.4.1`, which is
the newest release that still runs on macOS 11.0. MoltenVK `v1.4.2` raised its
runtime floor to macOS 12.0, above openQ4's documented `macOS 11` floor.
Advancing the MoltenVK pin past `v1.4.1` therefore requires the full floor
change listed above — Meson deployment target, `tools/build/package_nightly.py`
app metadata, `.github/workflows/manual-release.yml` package validation,
`BUILDING.md`, `docs/dev/platform-support.md`, `docs/user/getting-started.md`,
`assets/release/README.html`, `docs/dev/macos-signoff-evidence.md`, and the
macOS matrix and package policy tests — and must never be treated as routine
dependency maintenance. The provider pin is recorded in
`docs/dev/macos-moltenvk-provider-policy.md`.

macOS Vulkan evidence is additive to, and never a substitute for, the OpenGL and
Metal bridge signoff requirements below. There is no accepted real-Apple-hardware
evidence that MoltenVK-backed Vulkan renders correctly, so it is documented as an
experimental opt-in that may not work.

## Evidence Requirements

Every completed macOS signoff record must include:

- Architecture policy and actual CPU architecture.
- OS matrix role. Valid roles are:
  - `floor-candidate` for the documented macOS floor.
  - `latest-public-macos` for the latest public macOS release.
  - `current-hosted-ci-runner` for hosted CI package runs.
  - `current-manual-signoff`, the default for ad-hoc manual signoff runs
    (the guest-script default in
    `tools/macos/guest/openq4-macos-sync-build-test.sh`). Evidence recorded
    under this role counts toward neither the macOS floor nor latest-public
    promotion evidence; pass an explicit role when the run should count.
- macOS version and build.
- Kernel version.
- Xcode and macOS SDK version.
- Hardware model and CPU.
- Graphics bridge variant.
- OpenAL provider.
- Package artifact names and signing/notarization status.

First-class macOS support requires at least:

- OpenGL and Metal bridge signoff on the oldest supported macOS floor.
- OpenGL and Metal bridge signoff on the latest public macOS release.
- Real Apple-hardware or compliant Apple-VM evidence for every claimed
  architecture.
- Matching release notes that identify any untested, unsupported, or
  experimental macOS paths.
