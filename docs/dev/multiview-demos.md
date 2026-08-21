# Demo Playback and Multi-View Demo Architecture

## Status

The MVD core and the first unified demo-playback experience are implemented.
An openQ4 multiplayer server can record one full-world stream across every
active multiplayer instance, preserve the audience of reliable and unreliable
events, finalize it as a versioned `.mvd` file, validate it, and play it
through the Quake 4 server-demo free-fly/follow path.

The main-menu **Demos** library discovers native MVDs, openQ4 render demos,
command demos, unsupported legacy recordings, and incomplete recording
artifacts. Playback has one capability-gated control surface for pause/resume,
speed, relative and absolute seeking, stepping, MVD free roam/follow, and
stopping. Formats do not receive controls for state they did not record.

The format is intentionally new. An openQ4 `.mvd` is not labelled as a legacy
Quake 4 `.netdemo`, because the latter is a packet-oriented client recording
with different compatibility and safety properties.

## Competitive precedent

| Generation | Representative implementation | Model | Expectations it established |
|---|---|---|---|
| QuakeWorld | [MVDSV](https://github.com/QW-Group/mvdsv) and [ezQuake multiview](https://ezquake.com/docs/multiview.html) | The server records one stream containing every player POV. Messages carry all/single/multiple/stats routing and the same stream can feed QTV. | One recording for the match, instant POV switching, server-side `record`/`easyrecord`, automatic naming, downloads, autotracking, and broadcast use. |
| Quake II | [Q2PRO MVD](https://github.com/q2pro/q2pro/blob/master/doc/server.asciidoc) | A server-side dummy observer receives full entities, player state, and routed messages. `.mvd2` supports local playback and GTV relay. | Record without occupying a real player, play/seek controls, automatic limits, channel filtering, relay, and record-during-playback workflows. |
| Quake III Arena | [CPMA commands](https://www.playmorepromode.com/guides/cpma-commands), [client settings](https://www.playmorepromode.com/guides/cpma-client-settings), and [server settings](https://www.playmorepromode.com/guides/cpma-server-settings) | `mvd` records all POVs; playback can show all/none, highlight a primary view, and attach stats to that view. | Multi-window viewing, coach/team views, highlighted-player stats, automatic recording/action bits, powerup/killer tracking, and unattended broadcast operation. |
| Quake 4 | [idDevNet server network demos](https://iddevnet.dhewm3.org/quake4/NetworkDemos.html) and [benchmarking notes](https://iddevnet.dhewm3.org/quake4/Benchmarking.html) | The 1.1+ server demo records more than one client and permits free flight or player cycling. Competitive mods such as Q4Max built multipov and broadcast workflows on that base. | Familiar `recordNetDemo`/`playNetDemo`/`stopNetDemo` commands, free flight, cycling players, playback speed, filesystem/content compatibility checks, and competition-friendly automation. |

Across the generations, “multiview” means more than recording the spectator
camera. The durable user contract is:

- one authoritative match file, recorded by the server;
- every relevant player POV and full match state in that file;
- correct private, excluded, team/instance, positional, and global event routing;
- free-fly and low-friction player switching during playback;
- recording that is safe to leave enabled on a dedicated server;
- clear handling of incomplete, corrupt, oversized, and incompatible files;
- automation, seeking, richer view layouts, and live relay as natural follow-ons.

## openQ4 architecture

The Quake 4 game code already contained a dormant server-demo pseudo-client at
slot `MAX_CLIENTS`. Its original path can:

- build a delta snapshot without a player PVS, covering the complete active
  world for multiplayer instance 0;
- queue unreliable messages with either a target client or source PVS areas;
- serialize initial players, game state, and reliable state;
- apply server-demo snapshots to the pseudo-client during playback;
- filter events for the followed POV or current free-fly PVS;
- drive a free camera, switch followed players on attack, and leave follow mode
  on jump.

MVD 1.2 activates and extends that path:

1. `recordMVD` marks the game as server-demo recording and writes map plus
   initial network state.
2. Every game reliable is written once with its signed target, exclusion, or
   multiplayer-instance route. Unreliable target, PVS-area, and instance/PVS
   routes remain inside the game snapshot queue.
3. After authoritative server frames, the game module records periodic delta
   snapshots containing networked entities from every active instance rather
   than silently limiting tournament arenas to instance 0.
4. A clean stop writes an end record, flushes the file, closes it, and renames
   the staged `.mvd.part` file to `.mvd`.
5. `playMVD` loads the multiplayer game module when necessary, restores the
   recorded map and initial state, and advances the pseudo-client from checked
   records.

The session layer supplies the format-neutral library and player:

1. It enumerates `.mvd`, `.demo`, `.cdemo`, `.netdemo`, `.part`, and `.ucmd`
   files under `demos/`, including package-backed read-only files.
2. It uses bounded structural probes for render/command demos and checked MVD
   metadata rather than trusting the extension alone.
3. It assigns explicit capabilities to each entry and exposes only those
   actions in the GUI.
4. It routes native MVD, render-demo, and command-demo playback to their
   existing typed engine entry points.
5. It keeps unsupported retail and incomplete files visible with a useful
   status instead of trying to feed them to the wrong decoder.
6. It deletes only loose files that resolve beneath the save-path `demos/`
   directory; package-backed files remain read-only.

## Format and compatibility contract

The current writer produces `OQ4MVD` format `1.2`. The reader supports the
major-1 compatibility family, including formats `1.0` and `1.1`.

### Header

The header contains:

- an eight-byte magic value and byte-order marker;
- header byte length, allowing later versions to append fields;
- container major and minor versions;
- required and optional feature bitsets;
- Quake 4 network protocol major/minor;
- a game compatibility slot and simulation rate;
- recording start frame/time and snapshot interval;
- declaration/content checksum;
- an optional timeline-index record offset (`0` when absent);
- CRC-32 over the complete header except its CRC field.

A reader accepts the same container major even when the recorded minor is
newer, provided every required feature bit is supported. A different major is
rejected.

The 32-bit game compatibility slot deliberately stays in the same header
position:

- format 1.0 and 1.1 interpret it as the raw `GAME_API_VERSION`; playback uses
  an explicit allowlist of stream-compatible writers (currently API 39 and the
  current API), rather than treating every older ABI as safe;
- format 1.2 and newer interpret it as a packed MVD game-schema
  `major:minor` (`major << 16 | minor`) and ask the game module whether that
  schema is compatible.

This avoids rewriting the established major-1 header while decoupling future
recording compatibility from unrelated game API changes.

API 39 is explicitly retained because API 40 only appended the versioned MVD
callbacks: the version-1 snapshot and reliable record grammar remains
available in the current game module. Future legacy API exceptions must be
reviewed and added individually.

### Records

Every record has its own:

- sync marker and extensible header length;
- type, record version, and flags;
- bounded payload length;
- payload CRC-32;
- record-header CRC-32.

The record header is length-delimited before allocation. The current reader
caps a header at 256 bytes and a payload at 16 MiB.

Current record types are metadata, map state, initial network state, routed
reliable message, full-world snapshot, optional timeline index, and clean end.
Map state, network state, reliable messages, and snapshots are marked required.

An unknown optional record is skipped using its declared length. An unknown
required record, required record version, flag, or required feature bit stops
playback before its payload reaches game code. Existing record semantics must
never be silently changed; a changed payload gets a new record version.

Reliable and snapshot records have two supported schemas. Version 1 is retained
for format 1.0/1.1 playback. Version 2 is written by format 1.2 and adds the
instance byte required to route private arena traffic without leaking it into
another arena. Metadata, map state, network state, index, and end records remain
at record version 1.

Format 1.2 requires both `FULL_WORLD_INSTANCES` and `INSTANCE_ROUTING` feature
bits. A purported 1.2 file missing either bit is rejected rather than being
accepted as a misleading partial-world recording.

### Format 1.0, 1.1, and 1.2

The supported minor versions are intentionally incremental:

- A 1.0 recording has no timeline-index record and leaves its header index
  offset at zero. Its reliable and snapshot records use version 1. The current
  reader validates the stream and reconstructs its timeline by scanning checked
  snapshot records.
- A 1.1 recording can append an optional sparse index containing the first
  snapshot, approximately one entry per second, and the final snapshot. Each
  entry stores game time, file offset, and sequence, followed by the indexed
  end time. The header points to that record and the index is validated against
  bounded, strictly increasing times, offsets, and sequences.
- The index record is optional and length-delimited. Readers that do not know
  it can skip it; readers must not make it a prerequisite for decoding the
  unchanged major-1 snapshot stream.
- A 1.2 recording retains that optional index and writes reliable/snapshot
  record version 2. It records every active world instance and carries explicit
  instance routing for reliable and PVS-area unreliable messages.

The 1.1/1.2 index is a timeline directory, not a random-access checkpoint. It
provides a bounded, quick browser/startup summary without allocating an entry
for every snapshot. MVD snapshots remain a delta chain. Forward seeking
consumes records without real-time delay. A backward seek resets the recorded
map and initial network state, rewinds the stream, and replays from the
beginning under the per-frame `mvd_seekBudgetMS` work budget. This
replay-from-start path is also the compatibility fallback for 1.0 recordings.
A future direct-jump implementation must add independently restorable
keyframes; it must not treat an arbitrary delta snapshot as one.

The index remains optional even for a clean 1.2 recording. In particular, a
recording stopped before its first scheduled snapshot has no index, may report
zero snapshots, and is still a valid completed stream when its initialization
records and end counts agree. End-record validation counts the entire stream,
including initialization records, so no-index compatibility does not weaken
the clean-end check.

### Network and content compatibility

Container compatibility does not imply snapshot compatibility. Playback also
requires:

- the same Quake 4 network protocol major;
- read-only acceptance of the recorded protocol minor by
  `idGame::IsDemoProtocolCompatible` while inspecting the library, followed by
  `idGame::ValidateDemoProtocol` when playback starts and commits the game
  module's protocol state;
- the legacy game API match for format 1.0/1.1, or acceptance of the packed
  game schema by `idGame::IsMVDSchemaCompatible` for format 1.2+;
- the same simulation/user-command rate;
- the recorded declaration checksum by default.

`mvd_enforceContent 0` is an explicit diagnostic override for the last check.
It is not a promise that mismatched assets or declarations can be replayed
correctly.

Before native game parsers receive data, openQ4 validates the MVD
network-state structure, routed reliable-message envelope, snapshot queue
lengths, entity/client ranges, ordering, and record timeline. The matching
game-module readers also reject malformed nested messages and invalid
multiplayer indices. This is part of the format boundary: checksums prove that
bytes are unchanged, while structural validation proves they are safe and
coherent enough to decode.

Recorded map-state cvars are also treated as untrusted input. Only names
currently registered with `CVAR_NETWORKSYNC` may be restored; an arbitrary
recorded dictionary entry cannot set a local renderer, filesystem, console, or
developer cvar.

### Failure and privacy behavior

- New recordings use `.mvd.part`. Only a stream with a valid end record is
  atomically renamed to `.mvd`.
- A failed or crashed recording remains visibly partial and is never presented
  as complete.
- CRC failure or truncation stops at the damaged record.
- Snapshot, record, file-size, duration, and path limits bound resource use.
- Playback accepts at most 256 records while locating map/network
  initialization and processes at most 4096 stream records in one displayed
  frame. The separate seek time budget still limits replay work across frames.
- User-provided recording names are reduced to a safe basename and never
  overwrite an existing recording.
- Server and user state required for playback is recorded, but password keys
  are removed from server info. Rcon credentials are not part of the stream.

## Current operator interface

Select **Demos** on the main menu or run `demoMenu`. The browser offers
**All**, **Multi-view**, **Render**, **Legacy**, and **Incomplete** filters,
with name, detected type, map, date, duration, status, and selected-file
details. Enter or **Play** starts a supported entry. **Delete** is offered only
for a loose save-path file and always asks for confirmation.

During supported playback a compact status overlay shows the name, time,
duration, rate, and active view. Escape opens the interactive controls and
pauses playback. Closing the controls resumes only if the demo was running
before the menu opened.

The GUI provides:

- pause/resume and one-frame step;
- relative skips of -30, -10, +10, and +30 seconds;
- 0.25x, 0.5x, 1x, 2x, and 4x rate presets;
- MVD-only free roam and follow-next;
- stop and close.

The format-neutral console commands are:

| Command | Purpose |
|---|---|
| `demoMenu` | Open the library, or playback controls when a demo is active. |
| `demoPause [0\|1]` | Toggle pause, or set it explicitly. |
| `demoSpeed <0.05-16>` | Set playback rate. |
| `demoSeek <seconds>` | Seek to an absolute time from the demo start. |
| `demoSkip <seconds>` | Seek by a signed relative interval. |
| `demoStep` | Pause and advance one frame. |
| `demoFollow` | Follow the next player when the active backend is MVD. |
| `demoFreeRoam` | Enter free camera when the active backend is MVD. |
| `demoStop` | Stop the active demo. |

The MVD-specific interface remains available:

- `recordMVD [name]`, `stopMVD`, `playMVD <name>`, and `mvdInfo <name>`;
- `mvdPause [0|1]`, `mvdSeek <seconds>`, `mvdSkip <seconds>`, and
  `mvdSpeed <0.05-16>`;
- `mvdStep [frames]`, `mvdFollowNext`, and `mvdFreeRoam`.

Attack still switches to the next active player and jump leaves follow mode
for free flight. Quake 4-compatible aliases are `recordNetDemo`,
`stopNetDemo`, and `playNetDemo`. They create or read `.mvd`; they do not claim
legacy `.netdemo` compatibility.

Relevant MVD cvars are:

- `mvd_scale` and `mvd_paused` hold playback rate and pause state;
- `mvd_seekBudgetMS` bounds replay-seek work per rendered frame;
- `demo_renderSeekBudgetMS` is a cooperative render-demo replay budget checked
  between stream commands. An indivisible renderer command or map load can
  exceed it;
- `mvd_snapshotDelay` defaults to 50 ms;
- `mvd_maxSnapshotMB`, `mvd_maxSizeMB`, and
  `mvd_maxDurationMinutes` bound recording resources;
- `mvd_enforceContent` controls the declaration-checksum gate.

## Playback capability matrix

| Library entry | Play | Pause/rate | Seek/step | Camera | Notes |
|---|---:|---:|---:|---|---|
| Native openQ4 `.mvd` 1.0-1.2 | Yes | Yes | Yes, replay based | Full-world free roam and player follow | 1.0/1.1 retain legacy instance-0 capture semantics; protocol/content checks still apply. |
| Native or historical openQ4 render `.demo` | Yes | Yes | Yes, replay based | Fixed recorded camera | Presentation stream; it has no off-camera game state. |
| Retail Quake 4 render `.demo` | No | No | No | Recorded camera only in the original engine | Detected as legacy; the byte-oriented retail stream needs a separate decoder. |
| Retail Quake 4 `.netdemo` | No | No | No | Depends on original client/server recording | `NDMO` metadata is shown, but retail packet protocols are not decoded. |
| openQ4 `.cdemo` | Best effort | No | No | Simulation-defined | Unversioned developer artifact; safe only with the matching engine/game build. |
| `.mvd.part`, `.part`, or `.ucmd` | No | No | No | None | Shown as incomplete rather than a healthy recording. |

Render-demo wrapper compatibility includes the current `openQ4 RDEMO` and
historical `OpenQ4 RDEMO` spellings. `Quake4 RDEMO` is ambiguous: early
openQ4 and retail Quake 4 both used it. The decoder accepts it only when the
decoded first token proves it is the 32-bit openQ4 stream; a retail
byte-oriented stream is reported as unsupported.

Render demos can pause, change rate, step, and seek by consuming their command
stream. Rewinding restarts that render demo and replays commands with sound
muted until the target. Replay is advanced incrementally on the main thread
under the cooperative `demo_renderSeekBudgetMS` budget; the restart is deferred
so the seeking state can be presented first, although an indivisible map load
or renderer command can still take longer than the budget. Repeated seek
requests retarget the active operation, and mute state is restored on
completion, cancellation, failure, or stop. It cannot manufacture free-roam
or player-follow data.

Legacy render-demo decoding is best effort but no longer trusts the old stream.
Top-level tokens, hash-string tables, renderer payloads, indices, and sound
commands use exact checked reads and bounded values. A truncated or malformed
renderer or sound command closes the demo and returns to the menu with a
warning instead of escalating corrupt playback input into a fatal engine
error. Savegame sound-state failures retain their existing fatal policy; only
the demo-input path is made recoverable.

Command demos are intentionally not presented as portable recordings. Their
raw, unversioned command log and consistency checks make them sensitive to
engine/game changes; the unified UI exposes only play and stop. The browser
performs a bounded, nonfatal header and command-frame preflight before enabling
Play, and playback repeats that validation before and after map load.

## Delivery plan

### Phase 1: reliable core — complete

- Versioned, extensible, checksummed container.
- Server-side full-world capture across every active instance and reliable/
  unreliable audience routing.
- Staged finalization and bounded reads/writes.
- Map/initial-state restoration and pseudo-client playback.
- MVD 1.0/1.1 playback plus the 1.2 instance-aware writer, optional timeline
  index, and bounded replay-from-start seeking.
- Free-fly/follow controls, speed, pause, step, and info/validation command.
- Dedicated/client builds, gameplay round trip, corruption test, and source
  contract test.

### Phase 2: tournament operations

- `mvd_autoRecord` policies for warmup, countdown, match start/end, map change,
  and dedicated-server restart.
- Collision-resistant names built from UTC time, event, game type, map, round,
  and sanitized player/team names.
- Server-side list, retention, quota, and download policy.
- Structured markers for match transitions, timeouts, scores, and admin notes.
- A recovery command that scans a `.part`, verifies complete records, writes a
  recovery end marker to a new file, and never modifies the source.
- Console/Rcon status reporting and explicit reason codes for automatic stops.

### Phase 3: competitive playback UX — foundation complete

- Unified demo browser with format/status probing, filters, details, safe
  deletion, and explicit incomplete/read-only handling.
- Capability-gated playback overlay for MVD and render demos.
- Pause, slow/fast playback, single-step, relative skip, absolute seek, and
  bounded restart/replay rewind.
- Explicit MVD follow-next and free-roam actions alongside attack/jump.
- Historical openQ4 render-wrapper recognition and clear rejection of retail
  render and network demo streams.

Remaining competitive playback work:

- named player list, previous/direct follow, killer/powerup/team autotracking,
  and score/round markers;
- periodic independently restorable MVD keyframes for direct indexed jumps;
- CPMA-style highlighted primary view and multi-window `viewall` layouts with
  deterministic audio ownership;
- reverse-scrub presentation, timedemo/AVI integration, and generated
  thumbnails.

### Phase 4: broadcast and ecosystem

- A separately versioned live transport for Q4TV/GTV-style repeaters. The disk
  container remains the archive boundary; relay framing, authentication,
  backpressure, and reconnect semantics are not smuggled into the MVD 1.x
  container.
- Delayed spectator feeds, multiple downstream viewers, and record-while-relay.
- Optional chunk compression as a new feature/record version with strict
  decompressed-size limits.
- Metadata export for tournament tools without requiring full game playback.

## Update policy

Future changes follow these rules:

1. Additive metadata or records that old readers may ignore use optional
   records and increment the container minor when useful for discovery.
2. A new required capability gets a required feature bit and a new record
   version. Readers lacking it fail before playback.
3. Breaking header, ordering, timing, or baseline semantics require a new
   container major. The old decoder remains available for the supported
   compatibility window.
4. Game-level MVD changes increment the packed MVD schema and teach
   `IsMVDSchemaCompatible` exactly which older schemas remain safe. They do not
   inherit compatibility merely because the wider game API happens to match.
5. Snapshot protocol changes increment the network protocol and teach the pure
   `IsDemoProtocolCompatible` query plus playback's state-committing
   `ValidateDemoProtocol` exactly which older minors remain safe.
6. Each supported major keeps golden complete, zero-snapshot/no-index,
   truncated, CRC-corrupt, unknown-optional, unknown-required, older-minor, and
   newer-minor fixtures. Major-1 fixtures cover both record-v1 legacy routing
   and record-v2 instance routing.
7. Release qualification includes dedicated recording, listen-server
   recording, joins/leaves, bots, every game type, targeted/excluded/PVS
   and instance-routed effects, map-stop finalization, playback POV switching,
   and cross-platform reads on Windows, Linux, and macOS.
