# macOS OpenAL Provider Policy

Updated: 2026-06-30

This document records the current macOS audio-provider decision for openQ4.
It is intentionally conservative while macOS remains experimental, visual
parity issue #98 is open, and complete Apple-hardware signoff is outstanding.

## Current Release Decision

Experimental macOS release builds must use:

```text
-Dmacos_openal_provider=apple_framework
```

That option links Apple's system OpenAL framework through Meson
`dependency('appleframeworks', modules: ['OpenAL'], required: true)`. Release
workflows, package docs, and user-facing release notes must describe current
macOS audio as Apple's OpenAL framework, not bundled OpenAL Soft.

`-Dmacos_openal_provider=system` is migration-only. It is available for local
developer experiments that intentionally use a pkg-config-visible OpenAL Soft
dependency plus OpenAL Soft-style `AL/...` headers. The lookup is deliberately
pkg-config-only: if OpenAL Soft is not visible, configuration fails instead of
silently falling back to Apple's framework while compiling for the incompatible
`AL/...` header layout. Homebrew's keg-only installation normally needs:

```sh
export PKG_CONFIG_PATH="$(brew --prefix openal-soft)/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
```

This provider is not a release packaging target, not a support claim, and not
evidence that macOS packages bundle OpenAL Soft.

## Future OpenAL Soft Package Policy

Before OpenAL Soft becomes a macOS release provider, the project needs an
explicit package-design change covering all of these items:

- Library location: the bundled dylib must live in a reviewed app/package
  location, such as `openQ4.app/Contents/Frameworks/`, with no loose Homebrew,
  MacPorts, `/opt`, or `@rpath` dependency leaking into release binaries.
- Install names: every client, app executable, dedicated server, game dylib, and
  OpenAL Soft dylib must use package-relative install names such as
  `@executable_path/../Frameworks/...` or another reviewed package-relative
  path. Absolute local developer paths are forbidden.
- Codesigning: the OpenAL Soft dylib must be signed with the same ad-hoc or
  Developer ID policy as the rest of the package before app signing,
  notarization upload, archive validation, and DMG creation.
- License notice: release packages and docs must include the OpenAL Soft license
  notice and any required attribution before the dependency ships.
- Notarization allowlist: package and archive validators must add only the
  intended OpenAL Soft runtime paths to the app/package allowlist, while keeping
  `.dSYM`, Finder metadata, symlinks, case-fold collisions, stale frameworks,
  and unrelated dylibs rejected.

Until all of those requirements are implemented and validated, release packages
must remain on `macos_openal_provider=apple_framework`.

## Support Data

Crash reports should include the OpenAL log lines that already exist in
`openq4.log`:

- `OpenAL vendor:`
- `OpenAL renderer:`
- `OpenAL version:`
- `OpenAL requested device:`
- `OpenAL default device:`
- `OpenAL active device:`
- any `OpenAL EFX ...` warnings or status lines

The macOS support collector writes these lines to `logs/openal-summary.txt`
when it can find an existing `openq4.log`. The collector must not launch
openQ4 to obtain them. Support tooling must not launch openQ4 just to collect
OpenAL provider evidence.
