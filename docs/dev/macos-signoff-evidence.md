# macOS Signoff Evidence Index

Updated: 2026-06-30

This index records accepted Apple macOS runtime signoff evidence for openQ4. It is intentionally lightweight: large `.tar.gz` signoff archives stay in `.tmp/` while work is active and should be attached to release evidence, issue discussion, or another external artifact store instead of being committed to the repository.

macOS remains experimental unless the current release entry below points to a completed-checklist archive that passes validation.

## Evidence Rules

- Use only compliant Apple hardware, a VM running on Apple hardware, or a hosted Apple Mac provider.
- Collect final evidence with `tools/macos/Invoke-openQ4MacOSWorkflow.ps1 -Action CollectResults -MacOSRunId <id> -MacOSGraphicsBridge both -RequireCompletedSignoffChecklist`.
- Keep `<id>` to 80 or fewer characters using only letters, digits, dots, underscores, or dashes, starting with a letter or digit.
- Validate the collected archive with `python tools/macos/validate_signoff_archive.py <archive> --require-completed-checklist`.
- Record accepted evidence with `python tools/macos/record_signoff_evidence.py <archive> --version vX.Y.Z --update-index` after adding package artifact names, signing status, and release-note limitations.
- Record the SHA-256 of the exact archive that passed validation.
- Record both the openQ4 commit and the `openQ4-game` commit used to stage the game modules.
- Record the architecture policy, actual CPU architecture, and OS matrix role for the run. Use `OPENQ4_MACOS_OS_MATRIX_ROLE=floor-candidate` for oldest-supported-version signoff and `OPENQ4_MACOS_OS_MATRIX_ROLE=latest-public-macos` for current public macOS signoff.
- Record Xcode and macOS SDK versions from the signoff report so CI/package evidence can be matched to the Apple toolchain that produced it.
- Record the OpenAL provider, package artifact names, signing/notarization status, and any user-facing limitation that release notes must mention.
- Record the matching macOS dSYM symbol archive names and confirm that `SYMBOLS.txt` from the package root matches the runtime artifacts under test.
- Do not promote macOS beyond experimental until evidence covers both the documented floor and the latest public macOS release, or the support matrix explicitly narrows the claim.
- Use the renderer/backend policy in `docs/dev/macos-renderer-backend-policy.md` and the containment policy in `docs/dev/macos-native-backend-containment-policy.md`: record OpenGL and Metal bridge evidence separately, do not treat the Metal bridge as native Metal, and do not treat `platform_backend=native` as release support evidence.
- Do not mark a release entry complete if either bridge report has open checklist items.
- Do not mark a release entry complete if SP, MP, Finder launch, terminal launch, input, audio, display, or package-layout checks were skipped without a documented exception.
- Use the package contract in `docs/dev/macos-package-layout-and-release-policy.md`: the client is a self-contained drag-installable app with data under `Contents/Resources/baseoq4` and signed modules under `Contents/Frameworks`.
- Record mounted-DMG launch, dragged-app launch, whole-package loose-tool launch, embedded path/module checks, path-resolution logs, and Gatekeeper assessment for the package artifacts under test.

## Current Status

- [ ] No completed macOS first-class support evidence is recorded yet.
- [ ] The next macOS signoff archive must include OpenGL and Metal bridge result directories.
- [ ] The next macOS signoff archive must include `renderer-smoke`, `renderer-mp-smoke`, and `renderer-matrix` evidence for each bridge.
- [ ] The next macOS signoff archive must include completed manual checklist items for SP, MP, Finder launch, terminal launch, input, audio, display, and package behavior.
- [ ] The next macOS signoff archive must include mounted-DMG, independently dragged-app, whole-package loose-tool, embedded resource/module path, `fs_basepath`/`fs_cdpath`/`fs_savepath`, and Gatekeeper evidence.
- [ ] The next macOS signoff archive must include architecture policy, CPU architecture, OS matrix role, Xcode version, and macOS SDK version.
- [ ] The next macOS signoff archive must include openQ4 and `openQ4-game` commit fields in each bridge report.
- [ ] The next macOS signoff archive must keep OpenGL and Metal bridge renderer evidence separate and must not describe the Metal bridge as native Metal.
- [ ] Before first-class promotion, accepted evidence must include both a macOS floor-version signoff and a latest-public-macOS signoff for the current Apple Silicon/arm64 matrix.
- [ ] `docs/dev/release-completion.md` must reference the accepted evidence before macOS support claims are promoted.

## Current Release Evidence

Use this block for the active release candidate. Replace placeholder values only after the archive validates.

- Release/version:
- Support tier: experimental
- Evidence status: pending
- Run ID:
- Archive path or external artifact URL:
- Archive SHA-256:
- Validator command:
- Validator result:
- openQ4 commit:
- `openQ4-game` commit:
- Package artifacts:
- Symbol artifacts:
- `SYMBOLS.txt` manifest:
- Signing/notarization status:
- Architecture policy:
- Architecture:
- CPU architecture:
- OS matrix role:
- macOS floor evidence:
- Latest public macOS evidence:
- macOS version:
- Xcode version:
- macOS SDK version:
- Kernel:
- Hardware model:
- CPU:
- GPU/display:
- OpenAL provider:
- Graphics bridges tested:
- SP coverage:
- MP coverage:
- Dedicated server coverage:
- Finder launch coverage:
- Terminal launch coverage:
- Package layout contract:
- Mounted DMG launch coverage:
- Copied package launch coverage:
- App-only move behavior:
- Path resolution log coverage:
- Gatekeeper assessment:
- Input devices:
- Audio devices:
- Display modes:
- Known exceptions:
- Required release-note limitations:

Current release checklist:

- [ ] Archive validates with `--require-completed-checklist`.
- [ ] OpenGL report is present and complete.
- [ ] Metal bridge report is present and complete.
- [ ] `renderer-smoke` output exists for OpenGL.
- [ ] `renderer-smoke` output exists for Metal.
- [ ] `renderer-mp-smoke` output exists for OpenGL.
- [ ] `renderer-mp-smoke` output exists for Metal.
- [ ] `renderer-matrix` output exists for OpenGL.
- [ ] `renderer-matrix` output exists for Metal.
- [ ] SP entered an in-game map on real Apple hardware.
- [ ] MP loaded `game-mp`, started `mp/q4dm1`, connected a local client, and exited cleanly.
- [ ] Dedicated server startup was covered or explicitly documented as unsupported for this release.
- [ ] Finder or Desktop launcher startup was checked.
- [ ] Terminal startup was checked.
- [ ] Mounted signed/notarized DMG launch was checked, or unsigned archive behavior was recorded as an experimental exception.
- [ ] Dragging only `openQ4.app` to `/Applications` or another user-writable location was checked.
- [ ] Whole-package copied launch was checked for loose client, dedicated-server, and support-tool sibling-runtime discovery.
- [ ] `fs_basepath`, `fs_cdpath`, and `fs_savepath` were confirmed in logs for Finder/copied package and terminal launches.
- [ ] Gatekeeper assessment was checked for signed/notarized DMGs, or unsigned/unnotarized approval friction was recorded for development archives.
- [ ] Keyboard and mouse input were checked.
- [ ] Controller hotplug/rumble was checked, or unavailable hardware was recorded as an exception.
- [ ] Audio output, volume changes, and at least one device switch or reconnect were checked.
- [ ] Windowed, fullscreen, selected-display, and HiDPI/Retina behavior were checked.
- [ ] The app contained data under `Contents/Resources/baseoq4` and signed SP/MP modules under `Contents/Frameworks`, with no adjacent `baseoq4` duplicate.
- [ ] Matching `openq4-<version>-macos-arm64-<bridge>-symbols.tar.xz` dSYM archives were recorded and matched against package `SYMBOLS.txt` manifests.
- [ ] First-class macOS release artifacts are signed/notarized DMGs, or the release remains experimental and unsigned artifacts are labeled as development fallback output.
- [ ] Architecture policy, CPU architecture, and OS matrix role were recorded.
- [ ] Xcode and macOS SDK versions were recorded.
- [ ] macOS floor-version signoff was covered or documented as still required.
- [ ] Latest public macOS signoff was covered or documented as still required.
- [ ] Release notes mention that the Metal package is a bridge, not native Metal.
- [ ] Release notes do not imply that the native Cocoa/OpenGL backend is supported for release packages.
- [ ] Release notes mention arm64-only support.
- [ ] Release notes mention unsigned/unnotarized package behavior if unsigned artifacts are published.
- [ ] Release notes mention any renderer, audio, input, package, or MP limitation found during signoff.

## Evidence History

No accepted completed-checklist macOS signoff archive has been recorded yet.

Add new completed evidence records above this line, newest first, using the template below.

## Completed Evidence Template

```markdown
### vX.Y.Z - YYYY-MM-DD - <run-id>

- Release/version:
- Support tier:
- Run ID:
- Archive path or external artifact URL:
- Archive SHA-256:
- Validator command:
- Validator result:
- openQ4 commit:
- `openQ4-game` commit:
- Package artifacts:
- Symbol artifacts:
- `SYMBOLS.txt` manifest:
- Signing/notarization status:
- Architecture policy:
- Architecture:
- CPU architecture:
- OS matrix role:
- macOS floor evidence:
- Latest public macOS evidence:
- macOS version:
- Xcode version:
- macOS SDK version:
- Kernel:
- Hardware model:
- CPU:
- GPU/display:
- OpenAL provider:
- Graphics bridges tested:
- SP coverage:
- MP coverage:
- Dedicated server coverage:
- Finder launch coverage:
- Terminal launch coverage:
- Package layout contract:
- Mounted DMG launch coverage:
- Copied package launch coverage:
- App-only move behavior:
- Path resolution log coverage:
- Gatekeeper assessment:
- Input devices:
- Audio devices:
- Display modes:
- Known exceptions:
- Required release-note limitations:

Checklist:

- [ ] Archive validates with `--require-completed-checklist`.
- [ ] OpenGL and Metal bridge reports are present.
- [ ] `renderer-smoke`, `renderer-mp-smoke`, and `renderer-matrix` output exists for both bridges.
- [ ] Manual hardware checklist is complete in both bridge reports.
- [ ] Mounted-DMG, independently dragged-app, whole-package loose-tool, embedded resource/module path, path-resolution log, and Gatekeeper package UX checks are complete or documented as exceptions.
- [ ] Matching macOS dSYM symbol archives and `SYMBOLS.txt` manifests are recorded for each tested runtime package.
- [ ] Architecture policy, CPU architecture, OS matrix role, Xcode version, and macOS SDK version are recorded.
- [ ] macOS floor and latest-public-macOS coverage are recorded or called out as remaining blockers for first-class support.
- [ ] Renderer/backend limitations from `docs/dev/macos-renderer-backend-policy.md` are reflected in release completion and curated release notes.
- [ ] Release completion links to this evidence.
- [ ] Curated release notes reflect the tested support level and limitations.
```
