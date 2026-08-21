# openQ4 High-Framerate Rendering Plan (2026-04-15)

## Purpose

This document defines a staged implementation plan for allowing true high-refresh presentation in openQ4 while preserving Quake 4 gameplay behavior and stock-asset compatibility.

The goal is not to blindly raise the simulation tick. The goal is to let the engine present frames at modern refresh rates while keeping the authoritative game simulation stable and compatible.

## Recommended Target

- Primary supported target: `240 FPS` presentation.
- Stretch target after stabilization: `360 FPS` presentation.
- Baseline gameplay simulation target: keep `60 Hz` authoritative game/usercmd timing unless a later, separate project proves higher simulation rates safe.

Rationale:

- `240 Hz` is a practical modern high-refresh target and a good fit for current PC hardware.
- `360 Hz` is worth keeping in scope, but it should be treated as a follow-up validation target rather than the first milestone.
- Raising the core simulation tick to `120/240/360 Hz` would touch prediction, networking, demos, scripts, physics, AI, animation, and content assumptions all at once.

## Current State

openQ4 is currently structured around a `60 Hz` usercmd / async-tic model:

- `src/framework/UsercmdGen.h`
  - `USERCMD_HZ = 60`
  - `USERCMD_MSEC = 1000 / USERCMD_HZ`
- `src/framework/Common.h`
  - `GetUserCmdMSec()` returns `16`
  - `GetUserCmdHz()` returns `60`
- `src/framework/Common.cpp`
  - `idCommonLocal::Async()` advances `com_ticNumber`
  - `idCommonLocal::SingleAsyncTic()` increments `com_ticNumber`
- `src/framework/Session.cpp`
  - `idSessionLocal::Frame()` waits for `latchedTicNumber >= minTic` before continuing, which effectively ties frame progression to new tics
- `E:\Repositories\openQ4-game\src\game\Game_local.cpp`
  - game code reads `common->GetUserCmdMSec()` / `common->GetUserCmdHz()`
  - render view generation and per-frame game flow are built around that cadence

Important detail:

- the current `GetUserCmdMSec() == 16` representation is only an approximation of `60 Hz`
- `16 ms` is actually `62.5 Hz`
- that should be corrected before higher-framerate work is trusted

## Guiding Decisions

1. Keep authoritative gameplay timing at `60 Hz` for the first implementation.
2. Decouple presentation from simulation instead of globally increasing `USERCMD_HZ`.
3. Treat interpolation as required for "true" high-framerate support.
4. Preserve demo, cinematic, BSE, and multiplayer behavior unless explicitly reworked.
5. Validate both single-player and multiplayer in actual gameplay, not only at the main menu.

## Non-Goals For This Plan

- Shipping a `120/240/360 Hz` gameplay simulation change.
- Reworking multiplayer protocol or snapshot frequency as part of the first milestone.
- Changing stock content timing to chase higher benchmark numbers.

## Primary Touch Points

Engine:

- `src/framework/Common.h`
- `src/framework/Common.cpp`
- `src/framework/Session.h`
- `src/framework/Session.cpp`
- `src/framework/UsercmdGen.h`
- `src/framework/UsercmdGen.cpp`
- `src/framework/Console.cpp`
- `src/renderer/RenderWorld.cpp`
- `src/renderer/RenderWorld_demo.cpp`
- `src/sys/win32/win_main.cpp`

GameLibs:

- `E:\Repositories\openQ4-game\src\game\Game_local.cpp`
- `E:\Repositories\openQ4-game\src\game\Player.cpp`
- `E:\Repositories\openQ4-game\src\game\Entity.cpp`
- `E:\Repositories\openQ4-game\src\game\Camera.cpp`
- `E:\Repositories\openQ4-game\src\mpgame\Game_local.cpp`
- `E:\Repositories\openQ4-game\src\mpgame\Player.cpp`
- `E:\Repositories\openQ4-game\src\mpgame\Entity.cpp`
- `E:\Repositories\openQ4-game\src\mpgame\Camera.cpp`

## Phase 0: Measurement And Safety Rails

Before changing behavior, add enough diagnostics to measure the real runtime cadence.

Status: `Complete` as of `2026-04-16`.

Tasks:

- Add temporary or permanent instrumentation for:
  - async tic cadence
  - presentation cadence
  - sleep overshoot / wake jitter
  - number of game tics consumed per rendered frame
- Extend existing `com_showFPS` / diagnostics if needed so high-refresh behavior is visible in-engine.
- Log whether the game is currently:
  - simulation-bound
  - vsync-bound
  - presentation-cap-bound

Exit criteria:

- We can prove the current frame loop behavior in SP and MP.
- We can identify whether a change improves frame pacing or only changes an FPS counter.

Current progress:

- Added `com_showFramePacing` with:
  - `0` off
  - `1` in-engine HUD overlay
  - `2` HUD overlay plus console logging
- Added async timing aggregation so the engine can report:
  - average / min / max async delta
  - async effective Hz
  - async work time
  - wake jitter against the intended `60 Hz` tic cadence
- Added session-side presentation diagnostics for:
  - presentation-frame delta / Hz
  - tic delta consumed per rendered frame
  - game tics run per rendered frame
  - requested vs actual wait time
  - average oversleep / wake jitter
  - current pacing classification (`simulation`, `vsync`, `presentation-cap`, `uncapped`)
- Added an in-engine frame-pacing overlay under `src/framework/Console.cpp` so the current pacing mode is visible during runtime without relying on an external profiler.
- Added a direct frame-pacing snapshot path plus active-MP frame sampling from the common frame loop so local multiplayer autoscreenshot validation no longer loses its post-load pacing data when `session->Frame()` is bypassed.
- Validated a staged SP run to gameplay on `game/airdefense1` with `com_showFramePacing 2`, including an autoscreenshot and post-load pacing logs that settle onto the expected `60 Hz` async cadence.
- Validated a staged local MP run to gameplay on `mp/q4dm1` with `com_showFramePacing 2`, including server spawn, in-map autoscreenshot, and pacing classification logging.

Validation notes:

- The automated SP run now produces representative post-load pacing samples once the loading-continue gate is skipped for scripted validation.
- The automated MP run now produces a live autoscreenshot pacing snapshot and final summary after map load, so detached local-client validation no longer depends on the HUD overlay to confirm that post-load pacing data survived through teardown. Focused manual MP inspection is still the better source for representative presentation-Hz readings.

## Phase 1: Correct The Base 60 Hz Timing

The current `16 ms` approximation should be replaced with an exact representation of `60 Hz`.

Status: `Complete` as of `2026-04-16`.

Tasks:

- Replace hardcoded `16 ms` assumptions with a precise `60 Hz` representation.
- Prefer fractional accumulation or a numerator/denominator representation over integer truncation.
- Audit all callers that currently use:
  - `GetUserCmdMSec()`
  - `USERCMD_MSEC`
  - raw `16`-based assumptions tied to gameplay time
- Keep external gameplay behavior equivalent to the current intended `60 Hz` cadence.

Notes:

- This phase is a prerequisite for trustworthy high-refresh work.
- If exact timing requires API expansion, add a more precise helper rather than forcing everything through integer milliseconds.

Current progress:

- Added exact 60 Hz helper math in the engine and companion GameLibs instead of routing all timing through truncated `16 ms` integers.
- Moved async tic pacing and frame timestamps onto exact tic-time accumulation in the engine.
- Updated SP and MP game-frame bookkeeping, prediction/snapshot timing, and several one-tic gameplay checks to use exact tic timestamps.
- Moved generic script `wait` scheduling onto exact tic alignment in the SP and MP game libs so one-tic waits no longer round through legacy integer-millisecond timing.
- Switched script-facing frame-time queries to return the exact base-tic duration instead of alternating between truncated `16/17 ms` values.
- Replaced more “previous frame” camera, AI, and vehicle animation sampling that still treated the current frame span as a stand-in for the last exact tic.
- Updated cinematic end transitions to hold their one-frame post-stop state until the next exact tic instead of adding the current frame span.
- Cleaned up additional UI, loader, mini-game, and BSE one-frame assumptions so they no longer quietly run at `62.5 Hz`.
- Fixed remaining “next frame” gameplay hold/snapshot cases that were still using the current frame span as a proxy for the next exact tic.
- Taught the remaining legacy network one-tic defaults (`net_clientPrediction` and `net_clientLagOMeterResolution`) to follow the exact base-tic duration instead of hard-wiring `16 ms`.
- Added phase-0 runtime diagnostics alongside the cleanup so the exact-`60 Hz` baseline can be verified in-engine instead of inferred from code inspection alone.
- Revalidated the cleanup in staged SP and MP gameplay runs after the timing work landed.

Follow-up watch items:

- Keep an eye out for any smaller archived tuning defaults that may still deserve an explicit exact-tic alias during future validation, but treat that as opportunistic cleanup rather than a blocker for phase completion.

Exit criteria:

- Async tic pacing reflects true `60 Hz` timing.
- No obvious SP/MP behavior regression from the timing cleanup alone.

## Phase 2: Separate Presentation From Game-Tic Gating

openQ4 currently waits for a new tic before `idSessionLocal::Frame()` proceeds. That is the main architectural blocker.

Status: `Complete` as of `2026-04-16`.

Tasks:

- Refactor `idSessionLocal::Frame()` so the engine can render a presentation frame even when no new game tic has arrived.
- Keep `RunGameTic()` on its `60 Hz` cadence.
- Introduce a dedicated presentation cap cvar.
  - Suggested user-facing name: `com_maxfps`
  - Suggested supported range: `0` uncapped, otherwise clamp to a safe upper bound such as `1000`
- Add clear interaction rules for:
  - `r_swapInterval`
  - demos
  - cinematic playback
  - loading screens
  - minimized / background behavior

Design intent:

- multiple render frames may occur between simulation tics
- simulation still advances only when its own cadence says it should

Exit criteria:

- Engine can present above `60 FPS` without increasing the simulation tick.
- SP and MP remain functional with repeated-state rendering.

Current progress:

- Added `com_maxfps` as the new presentation-cap cvar in the common frame loop.
- Moved presentation throttling into `idCommonLocal::Frame()` so foreground rendering no longer depends on `idSessionLocal::Frame()` sleeping for new async tics.
- Kept demo playback and fixed-rate capture on explicit tic waits so the repeated-state path does not silently alter those timing-sensitive modes.
- Refactored normal single-player `idSessionLocal::Frame()` flow so it can render repeated-state frames when no new game tic has arrived, while still only running game tics when the authoritative async cadence advances.
- Added a Windows hidden/minimized safety clamp so a decoupled presentation path does not spin uncapped in the background.
- Switched the presentation-cap scheduler to SDL's high-resolution performance counter after validation exposed that the older millisecond sleep path undershot low caps too aggressively and the legacy Windows sys clock helpers were not a safe source for frame pacing.
- Refactored the foreground async-network path so listen-server / client netplay no longer blocks the render loop in `AsyncClient::RunFrame()` and `AsyncServer::RunFrame()` while waiting for the next `60 Hz` game frame; dedicated-style paths keep the old blocking behavior because they are not presenting repeated-state frames.
- Extended the same presentation throttle / real-time clock to blocking GUI loops (`idCommonLocal::GUIFrame()` and `ShowLoadingGui()`), so load screens and modal GUI redraw paths no longer bypass the new phase-2 pacing policy.
- Extended the blocking map-load pacifier and post-load loading-screen loops to the same presentation-time policy, so `PacifierUpdate()`, loading-bar ease-out, and the scripted post-load continue/menu transition no longer fall back to legacy one-tic redraw pacing whenever `com_maxfps` explicitly requests higher presentation rates.
- Extended the blocking wipe-completion loop to the same presentation-time scheduler, so `CompleteWipe()` no longer bypasses `com_maxfps` during map-transition fade completion.
- Added timed modal-GUI pacing harnesses for both wait-box and standard message-box flows, and fixed the scripted modal test path so it no longer consumes queued console commands from inside its own GUI pump loop.
- Hardened `syncNextGameFrame` so game-code requests from cinematic/savegame handoff paths now wait for the next real async tic instead of consuming an extra game frame early on a repeated-state presentation frame.
- Moved cinematic camera-view timing in the SP and MP player render paths onto a presentation-time source, so camera materials and cinematic HUD redraws continue to animate on repeated-state presentation frames instead of stalling at the `60 Hz` game-tic cadence.
- Added direct SP/MP cinematic validation commands (`cinematicStatus`, `listCinematics`, `startCinematic`, `stopCinematic`, `skipCinematic`) so phase-2 cinematic coverage no longer depends on brittle scripted trigger chains.
- Validated a staged single-player gameplay run on `game/airdefense1` with `r_swapInterval 0` and `com_maxfps 240`; the autoscreenshot snapshot now reports `present=11.03 ms (90.7 Hz)` while `async=16.67 ms (60.0 Hz)`, confirming presentation can outrun the simulation cadence without raising the sim tick.
- Validated a staged single-player gameplay run on `game/airdefense1` with `r_swapInterval 0` and `com_maxfps 30`; the autoscreenshot snapshot reports `present=33.83 ms (29.6 Hz)` with `async=16.67 ms (60.0 Hz)` and `bound=presentation-cap`, confirming the new cap path now throttles to the requested neighborhood instead of oversleeping into the mid-20s.
- Revalidated staged local multiplayer gameplay on `mp/q4dm1` with `r_swapInterval 0` and `com_maxfps 240` after the async-network change; the autoscreenshot snapshot now reports `present=9.59 ms (104.3 Hz)` while `async=16.67 ms (60.0 Hz)`, confirming foreground MP is no longer effectively hard-gated to one presentation frame per async tick.
- Revalidated the staged loading-screen / disconnect-to-menu flow on `mp/q4dm1` with `r_swapInterval 0` and `com_maxfps 240`; the loading GUI now stays in the expected high-refresh range instead of free-running into multi-kHz redraw, and the scripted snapshots report `present=5.47 ms (182.7 Hz)` in-game before disconnect plus `present=7.40 ms (135.2 Hz)` after returning to the main menu, confirming the phase-2 pacing path now carries through the map-load and menu transition.
- Revalidated the staged local MP load / disconnect flow again on `mp/q4dm1` after the pacifier and post-load-loop update; the early loading sample now reports `present=4.90 ms (204.2 Hz)` while the settled scripted snapshots report `present=9.37 ms (106.7 Hz)` in-game before disconnect plus `present=4.24 ms (236.0 Hz)` after returning to the main menu, confirming the remaining blocking load-screen path no longer collapses back to one presentation frame per `60 Hz` tic when `com_maxfps 240` is requested.
- Revalidated a staged single-player transition to `game/airdefense1` with `com_wipeSeconds 2`, `r_swapInterval 0`, and `com_maxfps 240`; the run completed through the modified blocking wipe path and the post-load snapshot reports `present=5.19 ms (192.6 Hz)` while `async=16.67 ms (60.0 Hz)`, confirming the transition still reaches repeated-state high-refresh gameplay after the wipe update.
- Revalidated fullscreen single-player gameplay with `r_swapInterval 1` and `com_maxfps 240`; on the current high-refresh display the autoscreenshot snapshot reports `present=6.97 ms (143.5 Hz)` while `async=16.67 ms (60.0 Hz)`, confirming vsync now caps presentation to display refresh instead of silently collapsing phase-2 behavior back to `60 FPS`.
- Revalidated fullscreen single-player gameplay with `r_swapInterval 1` and `com_maxfps 30`; the autoscreenshot snapshot reports `present=35.48 ms (28.2 Hz)` with `async=16.67 ms (60.0 Hz)` and `bound=presentation-cap`, which is consistent with a low requested cap being quantized to the monitor refresh divisor instead of landing on an arbitrary exact `30.0 Hz` under vsync.
- Revalidated staged single-player gameplay on `game/airdefense1` with `r_swapInterval 0` and `com_maxfps 240`, then exercised both modal GUI coverage paths in-session: the timed message-box snapshot reports `present=4.16 ms (240.5 Hz)` and the timed wait-box snapshot reports `present=4.16 ms (240.2 Hz)`, confirming the standard modal GUI loops now stay on the same presentation-timed path as gameplay instead of collapsing back to one redraw per async tic.
- Revalidated staged single-player cinematic handling on `game/airdefense1` with `r_swapInterval 0`, `com_maxfps 240`, and `g_autoSkipCinematics 0`; after map load, `startCinematic cin_opening` and `skipCinematic` produced a live handoff in the log (`cinematic entered`, `skipCinematic: requested=1`, `cinematic exited`, `syncNextGameFrame requested by game code`, `syncNextGameFrame consuming next async tic`) while the active cinematic stayed on the repeated-state presentation path at roughly `137-176 Hz`, confirming the phase-2 cinematic skip/exit path now survives high-refresh presentation without prematurely consuming an extra game frame.
- Revalidated the single-player loading-continue gate itself on `game/airdefense1` with `com_skipLoadingContinue 0`, `com_loadingContinueAutoAdvance 1000`, `r_swapInterval 0`, and `com_maxfps 240`; the clean staged run now logs `Loading continue gate entered (auto-advance 1000 ms)` followed by `Loading continue gate completed via auto-advance after 1004 ms`, then settles into repeated-state presentation at roughly `120-130 Hz`, confirming the last blocking SP post-load gate remains on the phase-2 presentation-timed path instead of collapsing back to one redraw per async tic.

Interaction notes from current validation:

- `r_swapInterval 1` does not imply `60 FPS`; on a high-refresh display it still allows presentation above `60 FPS` while the simulation remains at `60 Hz`.
- When `com_maxfps` is lower than display refresh and vsync is enabled, the effective presentation cadence follows the display's refresh quantization. Expect the result to land near the nearest refresh divisor rather than an exact arbitrary cap such as `30.0 Hz`.
- Windowed vsync validation is less authoritative than fullscreen on the current SDL3 path because compositor behavior can mask whether swap-interval control is actually the limiting factor.

## Phase 3: Presentation Interpolation

Repeated-state rendering is not enough for "true" high-framerate support. Motion smoothness requires interpolation.

Status: `Narrow first-person slice implemented on the current companion game-library branch; broader Phase 3 work and release qualification remain in progress` as of `2026-08-13`.

Implemented scope:

- SP and MP keep transient previous/current samples for first-person camera origin, camera axis, and FOV, plus the complete first-person viewmodel origin and axis. The local player, or the currently spectated player in MP, consumes those samples while preparing each `Draw()`.
- The presentation fraction is clamped from `0` to `1` across one authoritative `60 Hz` usercmd interval. This is previous-to-current interpolation, not extrapolation: it deliberately accepts at most one simulation tic of visual latency (about `16.7 ms`) rather than predicting a camera pose through collision or correction boundaries.
- Repeated-state draw preparation recalculates the render view and resubmits a copied viewmodel render entity only. It does not rerun player or weapon `Think()`, scripts, physics, networking, sound, or other gameplay work.
- Presentation samples and clock anchors are transient. The SP and MP `Save()` paths do not write them, and restore/map initialization reseeds them instead of changing the save-game or network contract.
- Live first-person `renderView.time` uses the presentation clock, while demo playback and timedemo remain on authoritative simulation time.
- Cadence/discontinuity checks snap instead of blending across missing tics, teleports, or other large changes. MP also disables interpolation while active prediction-error smoothing is correcting the viewed player.

Validation recorded for this slice:

- The SP/MP static parity and draw-boundary contract in `openQ4-game/tools/tests/presentation_interpolation_contract.py` passes.
- Both SP and MP GameLib builds pass.
- A windowed active-gameplay SP pass measured `86.2 Hz` presentation while simulation remained at `60 Hz`.
- An MP listen-server pass loaded the game module and map and produced an engine-side screenshot. The auxiliary loopback-client harness did not complete its requested client capture, although no fatal engine error was observed; this is not evidence of a successful two-client or remote-client validation pass.

Explicitly deferred:

- generic entity, mover, AI, local world-body, remote-player, projectile, dynamic-light, BSE/client-effect, trail, fracture, ragdoll, vehicle, and other bespoke visual-owner interpolation
- moving-platform-relative first-person special cases and alternate camera, security-camera, portal-sky, and cinematic-camera interpolation
- same-fire-frame weapon FX/tracer compensation and other presentation-time gameplay-adjacent cosmetic retraces
- raw-input compensation or presentation bias/extrapolation; the engine's optional presentation-input sampler is not consumed by the current game-library slice
- a successful full loopback-client capture, human SP/MP feel testing, cut-heavy cinematic coverage, Apple-platform testing, and dedicated high-refresh display/hardware qualification

Phase 3 exit criteria remain unmet until the first-person path passes those manual and platform checks and the broader visual scope is either implemented or deliberately scoped out for release.

## Phase 4: High-Refresh Compatibility Pass

Once decoupled presentation and interpolation are working, audit systems that can break at high presentation rates.

Status: `Engine-side compatibility groundwork landed; end-to-end game compatibility and release qualification remain in progress` as of `2026-08-13`.

Systems to verify:

- demo record / playback timing
- AVI capture path
- cinematics
- GUI timing and cursor behavior
- console FPS display and diagnostics
- BSE effect servicing and effect timestamps
- animation presentation assumptions
- sound synchronization expectations
- viewmodel depth hack and subview rendering

Special attention:

- `src/renderer/RenderWorld_demo.cpp`
- `src/framework/Session.cpp`
- `src/renderer/tr_light.cpp`
- any render path using `renderView.time`

Landed engine-side progress:

- The engine provides presentation cadence, timing diagnostics, caps, repeated-state session/network draw behavior, and modal GUI timing independently of the fixed `60 Hz` simulation described in Phases 1 and 2.
- Added an explicit renderer-side non-world 2D shader-time stamp and routed fullscreen GUI/material timing through it, so menu/loading/test-GUI passes no longer inherit a stale `tr.primaryRenderView.time` when they redraw outside the main 3D scene path.
- Fixed `idMaterial::UpdateCinematic()` to honor the caller-provided time instead of silently sampling cinematics from `tr.primaryRenderView.time`, closing a high-refresh compatibility gap for GUI/video-backed materials.
- Revalidated the staged timed modal GUI harness on the menu path with `r_swapInterval 0` and `com_maxfps 240`; the timed message-box snapshot reports `present=4.27 ms (234.1 Hz)`, confirming the focused Phase 4 UI timing cleanup still sustains repeated-state high-refresh presentation.
- Restored fixed-rate AVI capture to the exact-tic wait path in `idSessionLocal::Frame()`, so `aviGame` / other `aviCaptureMode` flows no longer rerun capture work on repeated-state presentation frames at the uncapped render rate.
- Revalidated a staged `aviGame` pass on `game/storage2` with `r_swapInterval 0`, `com_maxfps 240`, and the default `com_aviDemoTics 2`; the captured run reports `bound=simulation`, `ticDelta/frame=2.00`, `gameTics/frame=2.00`, and `present=32.38 ms (30.9 Hz)`, confirming the fixed-rate capture path now advances on the intended two-tic cadence instead of free-running at presentation speed.
- Audited the sound-listener timing boundary and confirmed that the high-level `gameTime` argument passed into `soundSystem->PlaceListener()` is currently a no-op in the engine sound world. Perceptual sound synchronization still needs the same manual qualification as the current first-person slice.
- Synced renderer subview `floatTime` setup to the subview's own `renderView.time` when secondary `viewDef`s are built from copied parent views, closing a stale-clock gap for remote camera/monitor renders and any subview material, cinematic, or BSE path that evaluates against `tr.viewDef->floatTime`.
- Reworked render-demo render-view/entity serialization to stop persisting raw `globalMaterial` / `remoteRenderView` pointers: new render demos now store render-view decl names plus full remote subview state, while playback of older demos safely clears those stale pointer fields instead of dereferencing process-local addresses, closing a compatibility gap for camera monitors, remote views, and other subview-driven material paths.
- Fixed renderer cinematic resets to honor the explicit caller-supplied millisecond timestamp instead of sampling the currently bound backend view clock, keeping GUI/video-backed material restarts aligned with presentation-time and render-demo-safe timing paths.
- Switched the legacy `com_showFPS` overlay off coarse `Sys_Milliseconds()` sampling and onto the engine's high-resolution clock, so the on-screen FPS readout stays trustworthy in the `240/360 Hz` range instead of quantizing around whole-millisecond frame deltas.
- Removed the remaining raw pointer-sentinel fields from current render-demo GUI/entity/light serialization, so new demos now persist explicit presence flags plus model/decl names for those references instead of truncating process-local addresses into `int` placeholders while older demos continue to replay through the legacy loader.
- Reconnected the session-side render-demo playback loop to `idRenderWorldLocal::ProcessDemoCommand()`, so recorded render frames now actually consume renderer demo packets again and advance `currentDemoRenderView`/GUI playback on frame boundaries instead of silently skipping all `DS_RENDER` work.
- Fixed the renderer-side demo map-load handoff so `ProcessDemoCommand()` now carries the pending post-load `demoTimeOffset` update across packet reads until the first `DC_RENDERVIEW`, instead of forgetting the `DC_LOADMAP` state before playback timing can be refreshed.
- Restored render-demo BSE/effect serialization as pointer-free v7 effect packets and added explicit renderer demo update/stop/delete effect commands, so recorded demos can recreate visible effect defs with their owner-time and stopped-state data instead of depending on process-local pointers or the current `renderView.time`.
- Revalidated a staged local MP `recordDemo` / `playDemo` pass on `mp/q4dm1` with `r_showDemo 1`; the resulting `phase4_effects.demo` now logs `write DC_UPDATE_EFFECTDEF` during capture, `reading a v7 render demo`, `DC_LOADMAP: maps/mp/q4dm1`, and repeated `DC_UPDATE_EFFECTDEF` entries during playback, confirming idle jump-pad, teleporter, item-hologram, and ambient steam BSE packets survive round-trip render-demo replay.
- Completed a second staged local MP render-demo lifecycle pass on `mp/q4dm1` that forces both effect-stop and effect-delete traffic; the resulting `phase4_effects_lifecycle.demo` logs `write DC_STOP_EFFECTDEF`, `write DC_DELETE_EFFECTDEF`, `reading a v7 render demo`, and matching playback-side `DC_STOP_EFFECTDEF` / `DC_DELETE_EFFECTDEF` entries, closing the remaining explicit Phase 4 render-demo effect-lifecycle validation gap.
- Corrected renderer effect-def lifetime handling so expired one-shot BSE effects now remain terminal until their owning `rvClientEffect` frees the handle, instead of being silently recreated by `UpdateEffectDef()` and replaying impact decals/sounds every frame after a bullet, shotgun, or projectile hit.
- Deduplicated renderer-side BSE servicing per rendered frame across multiple views. Broader game-side client-effect owner-time and entity-refresh behavior is not claimed by the current branch.
- Added renderer support for retaining model-space dynamic snapshots across transform-only entity-definition updates (`r_useRepeatedStateReuse`). This is compatible groundwork and does not imply that generic game entities are currently interpolated.
- Replaced the Linux `Sys_GetClockTicks()` / `Sys_ClockTicksPerSecond()` implementation (raw `rdtsc` calibrated against the momentary `/proc/cpuinfo` "cpu MHz" reading) with `CLOCK_MONOTONIC` nanoseconds, fixing a frequency-scaling skew that made the `com_showFPS` readout and the `com_maxfps` presentation throttle disagree with external present-rate monitors such as MangoHud on modern CPUs; CPU frequency for the processor summary and `SetMachineSpec()` now comes from a dedicated display-only `Sys_GetApproximateProcessorFrequencyHz()` on all platforms.
- Throttled the `com_showFPS` overlay to a 250 ms display-update window (frames counted against the wall clock) so the readout stays legible at uncapped rates instead of re-rounding a 4-frame average every presented frame; validated against the gameplay benchmark's independent pacing snapshot (`60.0 Hz` measured, `59-60fps` drawn under `com_maxfps 60`).

Exit criteria:

- No obvious time-base desync between presentation, demos, and special effects.
- High-refresh mode is stable across normal gameplay systems.

These exit criteria are not yet signed off. The engine-side items above remain valid, but broader game-side entity/projectile/FX compatibility and the manual/platform validation listed in Phase 3 are still outstanding.

## Phase 5: Supported Cap And User Exposure

After the architecture is stable, lock down the officially supported high-refresh target.

Recommendation:

- Officially support `240 FPS`.
- Allow higher values for experimentation.
- Treat `360 FPS` as supported only after dedicated validation passes succeed.

User-facing behavior to define:

- final cvar name and help text
- default value
- interaction with vsync
- whether `0` means uncapped
- whether menu / background / dedicated modes use separate caps

## Alternative Path Explicitly Rejected For The First Milestone

Do not start by raising `USERCMD_HZ` from `60` to `120/240/360`.

Why:

- game code consumes `common->GetUserCmdMSec()` and `common->GetUserCmdHz()` directly
- multiplayer prediction and async networking are built around the existing cadence
- demo capture / playback and timing-sensitive systems assume the current model
- content behavior may silently drift even if the engine appears stable

If higher simulation rates are ever pursued, that should be a separate design document after the presentation path is already decoupled.

## Validation Matrix

Per phase, validate at minimum:

- SP launch task to in-game movement and combat
- MP launch task to in-game movement and combat
- log review via `.home\\baseoq4\\logs\\openq4.log`
- vsync off and vsync on
- windowed and fullscreen
- low cap, `240`, and uncapped modes

Specific checks:

- camera pans feel smoother above `60 FPS`
- no runaway CPU spin when capped
- no accelerated or slowed gameplay
- no broken demo timing
- no stuck or jittering GUI cursor
- no visible weapon/viewmodel wobble caused by interpolation mismatch
- no BSE or particle timing anomalies during gameplay

## Suggested Delivery Order

1. Phase 0 instrumentation.
2. Phase 1 exact `60 Hz` cleanup.
3. Phase 2 presentation-frame decoupling.
4. Phase 3 local-player / camera interpolation.
5. Phase 4 compatibility sweep.
6. Expose and document `240 FPS` as the first supported high-refresh target.

## Definition Of Done For The First Milestone

The first milestone is complete when:

- openQ4 can present at `240 FPS`
- gameplay simulation still runs at the intended `60 Hz`
- camera and first-person presentation are genuinely smoother than the current build
- SP and MP gameplay remain stable
- no major regressions are found in demos, cinematics, GUI, or BSE-heavy scenes
