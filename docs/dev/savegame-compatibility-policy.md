# Savegame Compatibility Policy

This policy defines which openQ4 single-player saves the current runtime may
load. Reliability mechanisms and implementation detail are documented in
[Savegame Reliability](savegame-reliability.md).

## Current Policy at a Glance

| Save payload | Current decision |
| --- | --- |
| Version 3, exact wire-ABI stamp and valid integrity/footer | Supported format path; build/source drift is diagnostic only |
| Version 3, different wire-ABI stamp | Rejected before map teardown |
| Version 2, exact tuple in the allowlist below | Supported only on Windows/MSVC x64 little-endian `raw1` |
| Version 2, any other tuple | Rejected before map teardown |
| Unstamped legacy payload | Accepted only when its marker equals the current build and the runtime stamp is Windows/MSVC x64 little-endian `raw1` |
| Empty, negative-length, or over-512-MiB `.save` | Rejected before header or CRC preflight |
| Payload version newer than 3 | Rejected; no forward-compatibility guessing |
| Multiplayer/dedicated save | Not a supported player-facing feature |

The outer session-header reader accepts outer versions `1834`, `0`, and `1` so
that the payload can be examined. Passing that outer check does not override the
payload policy in this document.

## Version 3

Version 3 is the only format written by current builds. The complete file must be
no larger than 512 MiB, including its integrity trailer, and the payload wire-ABI
stamp must exactly equal the running build's stamp:

```text
<os>-<compiler-abi>-<architecture>-<endian>-raw1
```

Examples include `windows-msvcabi-x64-le-raw1`,
`linux-itaniumabi-x64-le-raw1`, and `macos-itaniumabi-arm64-le-raw1`.

Within v3, build number, generated source hash, and source-file count are recorded
for diagnosis but do not reject a save. The policy assumes every wire-incompatible
change bumps the gameplay compatibility version. A v3 save from another build is
therefore eligible only when the exact ABI stamp matches and both builds correctly
honored the v3 schema.

Eligibility is not runtime certification. For example, a Linux arm64 v3 save may
be format-eligible on another Linux arm64 `raw1` build, but it is supported for a
release only when that platform has matching candidate runtime evidence.

## Exact Version 2 Allowlist

Version 2 did not carry its own wire-ABI field. The current reader assigns v2 only
to the known Windows/MSVC x64 little-endian `raw1` lineage and accepts exactly
these `(build, source SHA-256, source-file count)` tuples:

| Build | Source SHA-256 | Files |
| ---: | --- | ---: |
| 639 | `d64f5bd29149262e67ce65107ea44b3f10af22011e7af354f23ca01550210fde` | 404 |
| 614 | `0c27fa5c6ef48b1bfe44c7be82b8a696772af4625eeefeed25de27da9640dd3f` | 404 |
| 556 | `871e5811e1732be750b18374b3d537aa38a91a050fb94cef847e2e3d39769cc2` | 218 |
| 544 | `82b545ffb5c9d8d27239eb8d1ed7eb5a22db1c40410dec4f3752f6f90fe76a60` | 218 |
| 544 | `ab567aef25905e8cf52e191523bc591f671b8cee3e63939a67af692bde3de446` | 218 |
| 544 | `9b26849ccdc3652aad892fdeeb5f219b631119fe601de00eb691fb5b4c13e02f` | 218 |

The three tuple fields plus the running Windows x64 `raw1` ABI are all required
in practice. A matching build alone, hash alone, hash prefix, or file count is
insufficient. Current writers never create new v2 saves.

An allowlist addition requires a reviewed byte-layout comparison, a successful
real SP save/load on the target Windows x64 runtime, corruption-contract coverage,
and a release-note entry. The allowlist must not be broadened speculatively.

## Unstamped Legacy Payloads

Unstamped payloads have no source snapshot, sync sequence, footer, or integrity
trailer. They are eligible only when:

- the first payload integer equals the running `BUILD_NUMBER`; and
- the running wire ABI is exactly `windows-msvcabi-x64-le-raw1`.

This is a narrow recovery path, not a general promise to load retail Quake 4,
arbitrary old openQ4, another operating system, or another architecture. Legacy
payloads receive bounded restore checks where available but cannot gain the v3
whole-file CRC/footer retroactively.

## Backward Compatibility

Backward compatibility means a newer runtime reading an older save. It is
supported only through an explicit decoder or allowlist:

- current v3 on the exact ABI path;
- the six exact v2 snapshots above on Windows x64 `raw1`; and
- the narrow same-build unstamped Windows x64 legacy path.

Unsupported saves fail closed before map teardown when total size, header,
version, ABI, allowlist, integrity, footer, or map preflight fails. The 512 MiB
limit applies equally to v3, approved v2, and unstamped legacy input. No in-place
conversion or repair tool is currently provided. Players should retain a copy of
important slots before upgrading, especially when moving from an unlisted
development build.

Removing an existing approved decoder is a release-policy change and requires an
upgrade note and, where practical, a migration path.

## Forward Compatibility

Forward compatibility means an older runtime reading a save written by a newer
format. It is not promised. Unknown payload, footer, integrity, or raw-layout
versions are rejected instead of being parsed as the nearest known layout.

When version 4 is introduced, its writer must not claim v3 compatibility unless
the emitted v3 bytes and semantics genuinely remain valid for an existing v3
reader. A new reader may retain a bounded v3 decoder, but the old reader is not
required to understand v4.

## Platform and Architecture Policy

The `raw1` stamp is deliberately restrictive because native-layout fields remain.
Current policy is:

- same OS ABI, compiler ABI, architecture, endian, and raw revision: format may
  be eligible;
- different operating system, compiler ABI, architecture, endian, or raw
  revision: reject;
- x64 and arm64 saves are not interchangeable;
- Windows, Linux, and macOS saves are not interchangeable;
- compilation on a platform does not prove save/load runtime support there;
- same-platform eligibility does not supersede the project's platform support
  and release evidence gates.

Cross-platform transfer can be considered only after the remaining raw inventory
is normalized, a portable wire revision is defined, fixtures are verified on each
supported ABI, and the policy is deliberately revised. It must not be inferred
from the typed fields already migrated.

## Schema Governance

The payload version is the compatibility boundary. Any change that alters the
ordered byte stream or the interpretation of a valid value must be classified
before merge.

### A payload-version bump is required when

- a field is added, removed, reordered, resized, or changes encoding;
- a list gains or loses an on-wire count or sentinel;
- an object/reference representation changes in a way an existing reader cannot
  preserve;
- native structure layout or raw-write meaning changes;
- SP and MP would otherwise interpret the same version differently; or
- a valid old payload would be consumed at a different offset.

### A payload-version bump is not normally required when

- a write is replaced by typed calls that emit byte-for-byte identical v3 data;
- a reader adds a bound that only rejects values impossible in a valid save;
- diagnostics, source hashing, lookup performance, or transaction handling change
  without changing payload bytes; or
- sidecar validation changes without changing the `.save` payload schema.

Every versioned change must update, in one change set:

1. the engine preflight constants and decoder;
2. both SP and MP GameLib constants, writers, and readers;
3. the wire-ABI/raw revision when native layout changes;
4. footer/integrity versions when those structures change;
5. corruption models, raw-write inventory, and ABI contracts;
6. this policy, reliability documentation, and player-facing upgrade notes.

The generated source hash is evidence and diagnosis for v3, not a substitute for
this versioning decision.

## Failure and User-Message Policy

Compatibility failures must identify the rejected layer—total size, outer
version, payload version, ABI, v2 snapshot, legacy build, CRC, footer, or
map—without attempting a partial restore. The running map remains active for
failures caught by engine preflight. Deeper object-specific semantic failures can
occur after teardown; they abort that restore and use the existing fresh-map
initialization fallback. There is no staged-world rollback that preserves the
former map after this point, and the failure must report the closest class/field
boundary available.

Save slots may remain visible when their bounded outer header is readable; menu
discovery intentionally does not checksum all payloads. Selecting an incompatible
slot must produce the precise failure and leave the original file untouched.

Release notes must state any compatibility break, supported older decoder, lack
of cross-platform transfer, and any required player action. They must not describe
build success or static ABI checks as runtime save/load validation.
