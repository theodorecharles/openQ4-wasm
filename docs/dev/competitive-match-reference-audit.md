# Competitive match reference audit

Date: 2026-08-03  
Status: Implementation audit; interactive runtime qualification is pending

This document records the behavioural comparison behind openQ4's competitive
match framework and the remaining gap to release qualification. The
authoritative design remains the
[competitive match framework specification](plans/2026-08-03-competitive-match-framework.md).
This audit does not turn reference-mod behaviour into a compatibility promise.

## Reading the status column

- **Integrated** means the behaviour is connected to the live multiplayer,
  UI or persistence adapter in the current working tree. It still needs any
  qualification named in the final column.
- **Qualification pending** means the implementation and automated contracts
  exist, but the named interactive, cross-role or gameplay matrix has not yet
  been signed off.
- **Remaining** means the concern is an accepted release closure item and is
  not described as delivered.
- **Deferred** is an explicit product boundary, not an accidental omission.
- **Rejected** means the precedent informed the design but is intentionally not
  part of openQ4.

The source status below is based on the local `OpenQ4` and `openQ4-game`
working trees on the date above. Automated contracts are not substituted for
the interactive runtime evidence named in the final column.

## openQ4 implementation source map

The main auditable boundaries are deliberately small:

- lifecycle, participants, roles, readiness and pause:
  [`MatchSession`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchSession.cpp);
- typed rule descriptors, transactions and built-in profiles:
  [`MatchRules`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchRules.cpp);
- bounded wire requests/results and operation descriptors:
  [`MatchProtocol`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchProtocol.cpp)
  and
  [`MatchOperations`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchOperations.cpp);
- challenge/proof referee authentication and throttling:
  [`MatchAuthentication`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchAuthentication.cpp);
- join evaluation, locks, queue, invitations and transaction plans:
  [`MatchTeams`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchTeams.cpp);
- best-of state and deterministic veto:
  [`MatchSeries`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchSeries.cpp);
- schema-versioned atomic cross-map state:
  [`MatchSeriesRecovery`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchSeriesRecovery.cpp)
  and
  [`MatchSeriesRecoveryFileSystem`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchSeriesRecoveryFileSystem.cpp);
- bounded series-result state and immutable atomic JSON:
  [`MatchSeriesReport`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchSeriesReport.cpp),
  [`MatchSeriesReportStorage`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchSeriesReportStorage.cpp)
  and
  [`MatchSeriesReportFileSystem`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchSeriesReportFileSystem.cpp);
- recipient authorization, tactical disclosure and serialization:
  [`MatchView`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchView.cpp)
  and
  [`MatchDisclosurePolicy`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchDisclosurePolicy.cpp);
- authoritative placed-major-item registry and recipient filtering:
  [`MatchItemTiming`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchItemTiming.cpp);
- audit journal and atomic JSON boundary:
  [`MatchEvidence`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchEvidence.cpp)
  and
  [`MatchEvidenceStorage`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchEvidenceStorage.cpp);
- bounded evidence projection:
  [`MatchEvidenceView`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchEvidenceView.cpp);
- presentation-only Match Control projection and row model:
  [`MatchControlModel`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/mp/match/MatchControlModel.cpp)
  and
  [`matchcontrol.gui`](https://github.com/themuffinator/OpenQ4/blob/main/content/baseoq4/pak0/guis/matchcontrol.gui);
- live game adapters:
  [`MultiplayerGame`](https://github.com/themuffinator/openQ4-game/blob/main/src/mpgame/MultiplayerGame.cpp); and
- engine-owned recording service:
  [`MultiViewDemo`](https://github.com/themuffinator/OpenQ4/blob/main/src/framework/async/MultiViewDemo.cpp)
  and
  [`NetworkSystem`](https://github.com/themuffinator/OpenQ4/blob/main/src/framework/async/NetworkSystem.cpp).

The local working trees may be ahead of those branch links while this feature
is being assembled; the filenames and boundaries are the audit authority for
the status matrix.

## Reference conclusions

The references agree on the human workflows more than on implementation:
players ready, captains manage their side, referees resolve exceptional states,
timeouts suspend play without consuming match time, spectators receive an
appropriate view, and completed matches leave useful evidence. Their internal
designs vary considerably.

- **Q4MAX** is the closest Quake 4 usability reference. Its documented command
  surface includes timeout/time-in, team-ready, player and spectator locks,
  spectator invitations, multipov and scoped referee access. These are useful
  workflow expectations, not APIs to reproduce. See the preserved
  [Q4MAX command summary](https://quake4.net/console-commands/) and
  [server setup notes](https://quake4.net/server-setup/).
- **CPMA** demonstrates that captain and coach workflows can operate a match
  without granting full server control. Its ready, timeout, captain, coach,
  invite, lock and referee commands are documented in the
  [CPMA command guide](https://www.playmorepromode.com/guides/cpma-commands/).
  Its mode system also shows why coherent per-gametype profiles are preferable
  to one enormous global configuration, while warning that weakly validated
  config composition is easy to misuse. See
  [CPMA server settings](https://cpma-news.org/guides/content/config/serversettings)
  and [custom modes](https://cpma-news.org/guides/content/config/custommodes).
- **OpenTDM** supplies a clear warmup/countdown/play/overtime/sudden-death/
  scoreboard lifecycle, captain-controlled team readiness and locks, timeouts,
  and privacy-aware live statistics. The local archive's principal evidence is
  `g_local.h`, `g_tdm_core.c`, `g_tdm_cmds.c` and `g_tdm_stats.c`; the upstream
  project and source location are documented at
  [opentdm.net](https://www.opentdm.net/) and
  [notr1ch/opentdm](https://github.com/notr1ch/opentdm).
- **WORR** demonstrates a modern session hub, a role-sensitive tournament veto,
  confirmations for destructive actions, an artifact catalog, and task-based
  documentation. The audited snapshot is commit
  [`46b0387`](https://github.com/DarkMatter-Productions/WORR/tree/46b03878154a7e9f6f384ef6468aee8ae2d8e068).
  Relevant sources include its
  [competitive server guide](https://github.com/DarkMatter-Productions/WORR/blob/46b03878154a7e9f6f384ef6468aee8ae2d8e068/docs-user/competitive-server-tools.md),
  [session-menu guide](https://github.com/DarkMatter-Productions/WORR/blob/46b03878154a7e9f6f384ef6468aee8ae2d8e068/docs-user/multiplayer-session-menu.md),
  [tournament core](https://github.com/DarkMatter-Productions/WORR/blob/46b03878154a7e9f6f384ef6468aee8ae2d8e068/src/game/sgame/match/tournament.cpp)
  and
  [match logging](https://github.com/DarkMatter-Productions/WORR/blob/46b03878154a7e9f6f384ef6468aee8ae2d8e068/src/game/sgame/match/match_logging.cpp).
- **AfterShock XE** is valuable both as a feature inventory and as negative
  design evidence. It includes warmup readiness, timeouts, rich votes,
  multiview and statistics, but its local `g_vote.c` ultimately schedules
  textual console commands and its match policy is spread across cvars and
  unrelated subsystems. openQ4 keeps the behaviours that help players and
  rejects that authority shape. Sources:
  [project overview](https://github.com/Irbyz/aftershock-xe),
  [vote implementation](https://github.com/Irbyz/aftershock-xe/blob/master/code/game/g_vote.c),
  [match loop](https://github.com/Irbyz/aftershock-xe/blob/master/code/game/g_main.c)
  and
  [change history](https://github.com/Irbyz/aftershock-xe/blob/master/CHANGELOG-AfterShock-XE.md).
- **Quake 4 itself** already provides the right engine-shaped foundation for a
  server recording and player-follow workflow. openQ4 extends that foundation
  instead of pretending a client recording is an authoritative match artifact;
  see the archived
  [idDevNet network-demo documentation](https://iddevnet.dhewm3.org/quake4/NetworkDemos.html)
  and openQ4's [MVD architecture](multiview-demos.md).

Q4MAX multipov is a behavioural reference, not a statement of current openQ4
transport support. openQ4 ships the connection-scoped broadcaster role and
server-owned MVD recording. The engine does not implement a reachable live
Q4TV/repeater transport; the match-view core's public-only repeater outcome is a
fail-closed boundary for a possible future adapter. Delayed broadcast and live
multi-POV composition remain deferred.

## Gap and decision matrix

| Concern | Reference lesson | openQ4 decision | Current status | Release gap / acceptance |
| --- | --- | --- | --- | --- |
| Match lifecycle | OpenTDM makes administrative and live phases explicit; Q4MAX exposes referee abort/ready control | Preserve Quake 4 wire phases, enforce one legal transition table and record a reason | **Integrated** through `mpMatchSession`; legacy game-state code is an adapter, not a second authority | Exercise every legal and illegal parent/round edge in each supported mode and confirm the remaining gameplay adapters cannot bypass it |
| Competition clock | AfterShock's history shows how many world systems can accidentally advance in a timeout | Keep network time monotonic, freeze match time, and rebase each gameplay deadline exactly once | **Integrated; qualification pending** | Complete the projectile, mover, item, powerup, weapon, animation, round and Tourney matrix over repeated pauses |
| Rules profiles | CPMA modes give each mode coherent settings, but permit minimally validated config composition | Typed descriptors, cross-field validation, atomic commit, stable digest and frozen map snapshot | **Integrated**, including Match Control staging/commit and legacy mirrors | Validate every profile/mode/map combination in live maps and stale-menu rejection at each rules boundary |
| Readiness | Q4MAX/CPMA/OpenTDM support player and captain readiness | Individual, team, combined or disabled policy with explicit blockers | **Integrated**, including player, captain and audited force-ready entry points | Qualify blocker presentation, countdown cancellation and disconnect/roster invalidation in every supported mode |
| Authority | CPMA distinguishes captain, coach and referee from full server administration | Connection-scoped participant IDs, role-derived capabilities and no implicit numeric hierarchy | **Integrated** with role/seat invariants and recipient-visible availability | Complete the cross-role reconnect and slot-reuse runtime matrix; never restore privilege from name, address or userinfo |
| Referee authentication | Q4MAX offers limited referee access | PBKDF2 challenge/proof, rate limits and an exclusive session-scoped referee grant; never rcon/filesystem power | **Integrated**, including localized sign-in/out and credential wiping | Exercise success, failure, throttling, logout, disconnect and map/session revocation through keyboard/controller UI |
| Team locks and joins | Q4MAX/CPMA/OpenTDM combine captain locks with invitations | One join evaluator returns allow, queue or deny and one transaction updates team/session state | **Integrated** across typed actions, userinfo reconciliation and spectator transitions | Run full, locked, invited, live, force-team and reconnect cases without a legacy side mutation escaping the evaluator |
| Roster seats and substitutes | Organised team mods distinguish roster membership from the current client slot | Stable session participant/seat model, invitations, role-compatible seats, atomic substitutions and narrow self-withdrawal | **Integrated**, including persistent substitute/bench membership and self-only coach/substitute departure without broad team-join authority | Qualify replacement disconnects, invitation expiry and repeated player/captain/coach/substitute transitions |
| Duel queue | CPMA and WORR keep extra duel players in a predictable waiting flow | Bounded FIFO queue keyed by session participant ID with join/defer/leave/promotion | **Integrated** with Match Control position/state; promotion still requires ready | Qualify disconnect, repeated defer, capacity and promotion ordering in live Duel |
| Tactical timeout | Q4MAX/CPMA/OpenTDM permit a side to stop and resume without general admin rights | Side budget, single owner, frame-boundary commit, configurable resume policy and resume countdown | **Integrated; qualification pending** | Complete simultaneous/duplicate request tests and the repeated-pause gameplay-freeze matrix |
| Technical pause | Referees need an exceptional pause distinct from a charged team timeout | Typed reason, referee/operator capability and no side-budget charge | **Integrated** with localized presentation and resume countdown | Qualify match-countdown and round-countdown coverage plus abort/forfeit while paused |
| Votes and proposals | Reference mods expose useful voting but several ultimately execute console text | A proposal stores one validated typed operation and a frozen human electorate | **Integrated**; managed legacy vote/cast paths reject while casual behaviour remains, and committing managed authority cancels an inherited vote even after it passed into delayed execution | Qualify global/side ballot display, threshold stability across disconnects and proposal revalidation on pass |
| Operation transport | Command-heavy mods duplicate validation at every entry point | One bounded schema, actor binding, optimistic control revision, authorization, cooldown and result | **Integrated** across GUI, compatibility commands, narrow dedicated-console adapters and passed proposals; legacy settings/kick/team/shuffle/restart/next-map adapters fail closed in managed sessions | Retain malformed/trailing/oversized fuzz coverage and verify identical live denial reasons at each entry point |
| Per-recipient state | CPMA coaches and Q4MAX spec locks imply that clients must not receive forbidden information | Authorize before serializing bounded `mpSessionView` v3; GUI never hides secrets it already received | **Integrated** for live player, coach, spectator, broadcaster and referee recipients; the pure repeater result is a future fail-closed boundary because no engine transport reaches it | Byte-test every supported live role during phase, role, lock and connection-generation changes; test the synthetic repeater policy separately without claiming a live transport |
| Coach and broadcaster views | CPMA supplies team-only coaching; Q4MAX supplies multipov | Explicit coach/broadcaster/referee audiences and fresh server checks for every follow transition | **Integrated**, with own-side coach follow and explicit broadcaster/referee paths; no live Q4TV/repeater path is shipped | Qualify every camera-cycle path and stale target change; captain spectator invitations remain fail-closed |
| Match Control UI | WORR demonstrates a stable task-oriented session hub and contextual destructive confirmations | One localized surface driven only by recipient views, descriptors and a bounded structured row model | **Integrated** across Status, Teams, Proposals, Rules, Series and Evidence | Validate windowed 16:9/4:3 layout, keyboard/controller navigation, credential clearing and every role workflow interactively |
| HUD and scoreboard | Competitive mods surface timeout, overtime, ready and series context near play | Minimal descriptor/state-key-driven context, not gametype-number branches | **Integrated** with a shared recipient-scoped role, phase, pause, readiness, timeout, proposal, series and authorized-item projection | Qualify layout at 16:9/4:3 and confirm casual play clears the single parent visibility gate |
| Series profiles | WORR demonstrates best-of setup and map order; tournament tools need deterministic state | Optional BO1/BO3/BO5 series with a bounded installed, mode-compatible pool and deterministic veto | **Integrated** for Duel/team modes; `si_mapCycle` or a deterministic installed-map pool supplies candidates | Qualify all profiles, pool bounds, insufficient pools and two-contestant admission in live maps |
| Veto and side choice | WORR exposes whose turn it is; competitive practice requires picks/bans and sometimes starting side | Typed BAN/PICK/SIDE steps with expected side and recorded initial side | **Integrated** with full view/history, safe exact-map scheduling and load-failure rollback | Run out-of-turn, duplicate, stale revision, starting-side and failed-load cases through Match Control |
| Cross-map recovery | WORR persists series progress; operators must not reconstruct state from logs | Versioned digest-protected record, fixed qpath, temp write plus atomic replace and no persisted connection identity | **Integrated** with stable series ID, map/result linkage, mode/pool validation and transactional restore; schema 3 checkpoints the series and mutable report draft as one checksummed transaction, while legacy schema 2 is diagnosis-only | Qualify interruption/restart; team-side recovery; and explicit connection-scoped Duel recovery through `matchSeriesBind` |
| Statistics privacy | OpenTDM hides opponent detail during live play; AfterShock restricts detailed stats until spectating/end | Evidence and recipient views have separate bounded, role-aware responsibilities | **Integrated** for authorized live vitals and finalized participant/team evidence; supported placed respawning major-item timers use the pause-safe match clock and project only to explicit broadcaster/referee recipients, with raw tokens never rendered | Verify forbidden enemy vitals and item timing are absent from player, coach, ordinary-spectator and synthetic future-repeater bytes rather than merely hidden by GUI; exercise pickup, respawn and repeated pauses |
| Audit/result artifact | WORR shows the value of schema-marked, discoverable artifacts | Bounded per-map schema-v2 journal/final JSON plus an immutable schema-1 series report, escaped serialization, fixed paths and atomic promotion | **Integrated** with series ID/session linkage, MVD artifact qpath/status, aggregate statistics where identity is safe, drop counters, transactional terminal ordering, Match Control status and Demos discovery | Run interrupted write, capacity, output-failure and final artifact inspection tests on the packaged runtime |
| Automatic MVD | Q4MAX/CPMA establish unattended competition recording; Quake 4 has a server-demo base | Managed profiles start openQ4 MVD at frozen countdown, link its qpath, and stop owned recording before report persistence | **Integrated; qualification pending**; a pre-existing manual recording remains operator-owned | Test start/stop/promotion failure isolation, distinguish `.part`, then play and seek the generated `.mvd` and reconcile it with JSON |
| Browser/mode truth | Older two-bit filters and placeholder modes mislead hosts and players | One public set: DM, Tourney, Team DM, CTF, One Flag CTF, Arena CTF, Arena One Flag CTF, DeadZone, Duel, Clan Arena, Freeze Tag and Red Rover | **Integrated registry/contracts** | Cross-check engine mirror, host menu, vote/map compatibility and browser filters at runtime; keep four reserved modes hidden |
| Persistent identity | Some mods approximate reconnect identity with names, GUIDs or addresses | Do not counterfeit identity; roles/readiness/queue votes are connection scoped | **Rejected/deferred** | A future cryptographic account/resume-token service may provide an explicit reattachment API |
| Remote web/brackets | Tournament ecosystems can schedule brackets and administer fleets | Keep brackets, league scheduling and remote administration outside the in-map aggregate | **Deferred** | Future tools consume typed session/evidence APIs; they do not gain game-process authority |
| Forced screenshots/client demos | Historical competition mods can issue client autoactions | Server MVD plus structured evidence; client capture remains local opt-in | **Rejected** | None |
| Delayed live broadcast | Q4MAX/CPMA multiview suggests a natural broadcast path | Correct recipient filtering and durable MVD first; do not label unrestricted live observation as delayed | **Deferred**; broadcaster views and server MVD are supported, but engine Q4TV/repeater transport, delay and live multi-POV are not implemented | Separate relay/delay design after role-filtered observation is proven; connect the existing pure public-only repeater boundary only through a future authenticated transport |

## Why this is one framework, not a mod-feature collage

The cohesive unit is a match operation, not a command name. A player pressing
Ready, a captain accepting a roster invitation, a referee committing rules and
a passed proposal all enter the same pipeline:

`bounded request -> bound participant -> capability and phase policy -> semantic validation -> one commit -> evidence -> recipient view`

This has several openQ4-specific benefits:

1. Quake 4's existing gameplay states and stock assets remain authoritative;
   the framework does not invent a parallel rules engine or require replacement
   content.
2. The engine/game-module boundary stays narrow. Secure random data, MVD and
   atomic filesystem operations are engine services; match policy stays in the
   game module.
3. Casual servers keep their existing behaviour because managed competition is
   enabled by an explicit typed profile.
4. Roles grant only match capabilities. A referee cannot silently become an
   rcon, ban-list or filesystem administrator.
5. UI, console compatibility and proposals cannot drift into independent
   authority systems because they consume the same descriptors and result
   reasons.

## Remaining release closure order

The architecture and end-to-end workflows are present. Release closure now
focuses on runtime qualification and evidence rather than adding another authority path:

1. Run the complete automated contract suite and warning-clean staged MP build
   after the final adapter changes.
2. Complete the windowed 16:9/4:3 HUD, scoreboard and Match Control matrix for
   player, captain, coach, broadcaster, referee and local operator.
3. Prove the supported live-role redaction, item-timing and camera-follow matrix
   from encoded bytes, plus the fail-closed captain spectator-invitation
   boundary. Exercise the synthetic public-only repeater policy separately; no
   live Q4TV/repeater transport exists to qualify.
4. Complete the repeated-pause world matrix and supported-mode lifecycle tests.
5. Run BO1/BO3/BO5 across maps, interrupted recovery, team-side recovery and
   explicit Duel `matchSeriesBind` recovery.
6. Inspect atomically persisted JSON, exercise failure isolation and play the
   linked generated MVD through the Demos library.

The working tree should therefore be described as an implemented competitive
framework awaiting interactive release qualification, while stopping short of
an independent tournament-certification claim.
