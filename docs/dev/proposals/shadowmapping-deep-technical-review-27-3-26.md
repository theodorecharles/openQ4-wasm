# openQ4 Shadow Mapping Deep Technical Review and Productionization Plan

## Scope, constraints, and evaluation criteria

openQ4’s renderer is idTech4-derived (the lineage of entity["video_game","Doom 3","idtech4 game 2004"] / entity["video_game","Quake 4","idtech4 game 2005"]), which strongly shapes what “production-ready” means in practice: many lights, forward additive lighting passes (“interactions”), and historically a heavy reliance on stencil shadow volumes. fileciteturn47file0L1-L1

Within that context, the current goal is not simply “make a shadow map,” but to make a shadowing system that is:

- **Complete enough** to cover the main light types and common material cases without silently regressing to wrong shadows (or no shadows).
- **High-quality** in the ways humans notice immediately: contact fidelity (no floating/peter-panning), stable temporal behavior (no cascade shimmer/swim), and clean edges appropriate to the light size.
- **Accurate enough** for the engine’s intended look: consistent depth spaces, correct occluder selection, and physically plausible transmission for optional transparency shadowing (within idTech4’s material semantics).
- **Efficient** under idTech4’s “many local lights” workload.
- **Robust** across driver capability variability and failure modes (shader compile/link, FBO completeness, state leaks).

openQ4 already exposes a broad set of CVars and debug modes for shadow maps (including CSM, hashed alpha cutouts, and experimental translucent moments), so this review treats configurability as a core requirement, not an afterthought. fileciteturn49file0L1-L1 fileciteturn48file0L1-L1

## Current openQ4 shadow mapping architecture

openQ4’s user-facing documentation describes a shadow-map pipeline that supports:

- **Projected-light shadow maps** (spot/projector-style idTech4 lights)
- **Point-light shadow maps** (omni lights)
- **Projected-light CSM** (up to 4 cascades packed in an atlas)
- **Cutout (alpha-tested) shadowing** via hashed alpha testing by default
- **Experimental blended/translucent “moments” shadow overlay** (colored transmission, MRT-based) fileciteturn49file0L1-L1

It also explicitly states that the engine **falls back to the legacy shadow path** when the shadow-map path is unavailable or fails for a given light, rather than leaving the light unshadowed. fileciteturn49file0L1-L1

### Caster classification and eligibility

At the interaction-building stage, openQ4 constructs dedicated draw-surface chains for shadow-map casters:

- `globalShadowMapCasters` / `localShadowMapCasters` for opaque/perforated casters.
- `globalTranslucentShadowMapCasters` / `localTranslucentShadowMapCasters` for blended casters, only when the experimental translucent moments feature is enabled and hardware limits allow it (GLSL availability, enough texture units, ≥3 draw buffers/attachments, cubemap support for point lights). fileciteturn47file0L1-L1

It also filters out problematic categories (view-only entities, depth-hacked models, GUI/subview materials) for caster inclusion, which is the correct “production hygiene” direction for stability and predictability. fileciteturn47file0L1-L1

### Shader programs actually used for shadow maps

Despite the renderer being “ARB2” overall, the shadow-map path is implemented in **GLSL 1.10** programs (e.g., `#version 110`) compiled through ARB shader objects. This is visible in the shipped shadow shaders for projected and point interactions and casters. fileciteturn24file0L1-L1 fileciteturn25file0L1-L1 fileciteturn42file0L1-L1

Key examples:

- **Projected cutout caster** supports hashed alpha testing (`uAlphaHashEnabled`) using `gl_FragCoord.xy` as the hash domain, discarding fragments probabilistically based on derived “coverage” from alpha and the alpha-test reference. fileciteturn38file0L1-L1
- **Point shadow caster** packs radial depth into two channels (a ~16-bit scheme) and optionally applies alpha testing / hashed alpha testing before writing packed depth. fileciteturn42file0L1-L1
- **Translucent caster (projected and point)** emits per-channel optical-depth moments into three MRT outputs (R/G/B separated), using an optical-depth transform `-log(1 - alpha)` and depth moments in terms of `gl_FragCoord.z` (projected) or normalized radial distance (point). fileciteturn40file0L1-L1 fileciteturn44file0L1-L1

This is already a strong foundation: GLSL is the right tool for CSM selection logic, robust coordinate checks, and any future filtering/transmission models.

## Findings on quality, accuracy, and artifact risk

### Known critical failures and what they imply

openQ4’s own internal triage notes two severe observed failures in the new shadow mapping path:

- **Peter Panning** (shadows detached from casters).
- **“Unravelled” / scattered projected shadows** when angled surface lights cast shadows, or when upright surface lights cast onto angled receivers. fileciteturn34file0L1-L1

The triage notes that “no combination of shadowmapping CVars resolves either issue,” which is a strong indicator that the root cause is not “tuning,” but **a correctness defect** in one of these categories: depth space mismatch, wrong resource binding / stale atlas tile, invalid projective coordinates (bad `w` divide / NaNs), caster geometry corruption (cache/VBO/index issues), or GL state leakage (viewport/scissor/FBO). fileciteturn34file0L1-L1

image_group{"layout":"carousel","aspect_ratio":"16:9","query":["shadow mapping peter panning vs shadow acne diagram","cascaded shadow map shimmering stabilization texel snapping diagram","shadow map atlas cascade layout diagram"],"num_per_query":1}

### Bias design: what’s implemented and what still needs hardening

openQ4 exposes both **caster-side polygon offset** controls (`r_shadowMapPolygonFactor`, `r_shadowMapPolygonOffset`) and **receiver-side bias** controls for projected and point lights (`r_shadowMapBias`, `r_shadowMapNormalBias`, `r_shadowMapPointBias`, `r_shadowMapPointNormalBias`). fileciteturn49file0L1-L1 fileciteturn48file0L1-L1 fileciteturn51file0L1-L1

OpenGL’s polygon offset is explicitly defined as an offset of the form `factor * DZ + r * units`, applied after interpolation and before depth test/write. citeturn8search0turn8search7 This matches the intended use in shadow maps: reducing self-shadowing on the caster pass, especially at grazing angles.

However, the triaged symptoms strongly suggest that the current “panning” may be **structural**, not purely over-biasing. Productionization requires a strict separation of concerns:

- **First** prove that the shadow map actually contains correct caster depth silhouettes and that the receiver is sampling the correct region/texture. fileciteturn34file0L1-L1
- **Then** tune bias (including per-cascade scaling) to trade acne ↔ panning in a predictable, monotonic way. fileciteturn49file0L1-L1

A key upgrade path for large PCF kernels is **receiver-plane depth bias** (derivative-based biasing), which Microsoft’s CSM guidance calls out as a method that can be necessary for large kernels while avoiding excessive peter-panning (at additional shader cost). citeturn9search0

### CSM quality: what’s already present and what is still missing

openQ4’s CSM feature set is already aligned with common practice: configurable cascade count (1–4), camera distance range, a λ blend between uniform/log split placement, cascade blending, and stabilization (“snap bounds to texels”). fileciteturn49file0L1-L1 fileciteturn48file0L1-L1

The Microsoft CSM guidance highlights several pitfalls that map directly to openQ4’s tuning knobs and current failure modes:

- CSM exists primarily to combat **perspective aliasing** by allocating more shadow resolution near the eye. citeturn9search0
- **Depth bias becomes more important** with large PCF kernels because neighboring taps refer to different depths, increasing erroneous self-shadowing unless biasing is handled carefully. citeturn9search0
- When rendering cascades into a single large buffer, you need **padding for PCF kernels**, or sampling crosses cascade boundaries unless you clamp or add a guard band. citeturn9search0

openQ4 exposes both a projected padding value (`r_shadowMapProjectionPad`) and a cascade blend fraction (`r_shadowMapCascadeBlend`), which is consistent with the need to avoid edge leakage and seams. fileciteturn49file0L1-L1

What’s still needed for “production-ready” CSM in this engine is not more knobs—it’s **strong invariants and automatic safeguards**:

- A deterministic “valid projection” contract (projective `w` handling, NaN/Inf handling, strict atlas bounds).
- A per-light decision system (when CSM is appropriate vs. when it should be disabled for that light to avoid unstable projections).
- A robust cascade debug HUD that makes wrong cascade selection, atlas misaddressing, and invalid coordinates immediately visible (your debug modes are a good start, but they need to be treated as first-class QA tools). fileciteturn49file0L1-L1 fileciteturn48file0L1-L1

### Transparency shadowing: cutouts vs. true translucency

#### Cutouts (alpha-tested / perforated)

openQ4’s default for cutouts is **hashed alpha**, implemented directly in the caster shader. fileciteturn49file0L1-L1 fileciteturn38file0L1-L1

This aligns with the primary reference on hashed alpha testing by entity["people","Chris Wyman","graphics researcher"] and entity["people","Morgan McGuire","graphics researcher"], which explains that hashed alpha addresses the common failure mode where alpha-tested geometry disappears under minification, trading it for controlled noise with improved stability. citeturn8search3

From a production-quality perspective, openQ4’s cutout approach is directionally strong, but it needs two additional hardening steps:

- **Stability under CSM movement** (hashed sampling anchored in shadow-map texels is only stable if cascade projection is stabilized; otherwise it can shimmer).
- **Consistent material semantics** (ensure the shadow caster uses the same alpha test thresholds/texture coordinates as the surface’s intended cutout behavior; your shader infrastructure supports alpha ref and matrix rows already, but this must be validated against real idTech4 content patterns). fileciteturn39file0L1-L1 fileciteturn38file0L1-L1

#### Blended/translucent transmission (experimental moments overlay)

openQ4’s translucent shadowing is explicitly described as **experimental**, conservative in supported stage patterns, and implemented as an additional overlay pass requiring extra MRT attachments and extra samplers. fileciteturn49file0L1-L1

Technically, the caster shaders convert absorption-like alpha into **optical depth** (`-log(1-alpha)`) and accumulate depth moments per color channel into three render targets. fileciteturn40file0L1-L1 This is a physically motivated direction (Beer–Lambert style transmittance models are naturally exponential in optical depth), but a moments-based model is notorious for **leakage and reconstruction artifacts** when not formulated carefully.

If your goal is “highest quality possible” translucent occluder shadowing within an OpenGL shadow-map framework, the most relevant modern reference class is **Moment Shadow Maps**, which explicitly covers soft shadows and translucent occluders and provides a mathematically grounded moment reconstruction approach (including improved variants). citeturn9search36

openQ4 is already storing four values per channel (`tau, tau*z, tau*z^2, tau*z^3`), which is strongly suggestive of a “4-moment” intent. fileciteturn40file0L1-L1 Productionization here means: either commit to a well-defined MSM-style reconstruction (with known error bounds and mitigation), or keep this feature clearly “experimental/artist-driven” with strict guardrails and easy disable.

## Findings on performance, scalability, and robustness

### Scalability under idTech4’s “many lights” workload

Shadow mapping is fundamentally a **light-dependent extra render pass**. In idTech4-style scenes, dozens of local lights can be active, and doing per-light shadow maps (plus CSM multi-cascade, plus point-light cubemap faces) can explode GPU cost.

openQ4 already attempts several critical mitigations:

- It only links eligible casters, skips GUI/subview materials, and avoids including view-only entities or depth-hacked models in caster lists. fileciteturn47file0L1-L1
- It uses cached ambient/index buffers where possible and touches caches to avoid unintended purges. fileciteturn47file0L1-L1
- It gates translucent moments by explicit CVar and by hard GPU capability checks. fileciteturn47file0L1-L1 fileciteturn49file0L1-L1

That said, production readiness requires a step beyond “it works”: you need a **policy system** to stop shadow maps from becoming your top frame-time driver.

At minimum, implement per-light heuristics or authoring controls such as: “CSM only for global/directional lights,” resolution scaling based on screen impact, update rate throttling for lights that don’t move, and strict budgets that degrade gracefully (drop cascade count, reduce resolution, disable translucent overlay) rather than producing hitches.

### Robustness: shader compilation, capability detection, and fallbacks

openQ4 explicitly detects GLSL availability via ARB shader object extensions (and ensures the “ARB2” path can run). fileciteturn51file0L1-L1

Two high-value robustness properties already exist:

- shadow-map features are guarded by capability checks (texture units, MRT counts), and
- the user-facing docs state that failure falls back to legacy shadowing rather than silently producing unshadowed lights. fileciteturn47file0L1-L1 fileciteturn49file0L1-L1

However, the presence of severe artifacts that resist CVar tuning strongly suggests at least one of these robustness issues is still present:

- **GL state leakage** (viewport/scissor/FBO depth attachments not restored cleanly between passes).
- **Resource binding mismatches** (sampling wrong texture unit, stale atlas tile, wrong sampler state).
- **Projective degeneracy** (invalid `w`, NaNs) that causes undefined sampling and scattered results, as explicitly hypothesized in the repo’s own triage. fileciteturn34file0L1-L1

For production, robustness must be enforced by “hard” debug tooling: one-frame overlays for atlas and per-cascade validity plus per-light reporting should be easy to turn on and must be trusted. fileciteturn49file0L1-L1

## ARB assembly vs GLSL for shadow mapping in openQ4

### What the codebase is actually doing today

openQ4’s renderer is positioned as “ARB2,” but it also supports GLSL programs through ARB shader objects (`GL_ARB_shader_objects`, etc.). fileciteturn51file0L1-L1

The actual shadow-map implementation is already **GLSL-based** (GLSL 1.10), as shown by the shipped `.vs/.fs` shadow caster and interaction programs. fileciteturn24file0L1-L1 fileciteturn38file0L1-L1

So the real decision is not “ARB vs GLSL for shadow mapping,” but:

- Do you keep shadow mapping as a GLSL “island” within the ARB2 renderer (very reasonable)?
- Or do you migrate more of the renderer to GLSL over time (potentially beneficial, but higher risk)?

### Suitability assessment

For **production-quality shadow mapping**, GLSL is the more suitable approach because:

- CSM selection/blending, robust coordinate validation, and any advanced filtering or moment methods are drastically more maintainable in GLSL than ARB assembly.
- The current implementation already relies on GLSL for hashed alpha cutouts and for the translucent moments overlay. fileciteturn38file0L1-L1 fileciteturn40file0L1-L1
- The immediate blockers you are facing (“unravelled” scattering, persistent peter-panning) are exactly the class of issues where you want rapid iteration, debug instrumentation, and branchable logic in shaders—again best served by GLSL.

ARB assembly is still defensible as a legacy fallback for older hardware/driver stacks, but it should not be the “primary innovation path” for shadow quality or correctness.

### Recommendation

Keep the shadow mapping path GLSL-first, and invest in:

- a consistent shader loading/validation framework,
- strict “validity” contracts for the shadow programs (compile/link must be treated as hard gates), and
- better debug modes and automated tests tied to the GLSL path.

At the renderer-architecture level, preserve ARB assembly for compatibility if needed, but treat GLSL as the production path for shadowing features going forward. fileciteturn51file0L1-L1

## Production-ready implementation plan

This plan is ordered to eliminate correctness blockers first (because no amount of “quality tuning” matters if the projection is wrong), and only then expand quality and performance.

### Correctness lockdown and defect isolation

First, force the pipeline into a state where you can unambiguously answer: “Is the shadow map content correct?” and “Are receiver coordinates valid?”

- **Atlas visualization is mandatory**: make `r_shadowMapDebugMode 1` (atlas/depth view) authoritative, and extend it so that every cascade tile/face is clearly delineated and stamped (tile index markers). fileciteturn49file0L1-L1 fileciteturn48file0L1-L1
- **Receiver validity overlays**: treat projected-UV, projected-depth, projected-W, and invalid-mask debug modes as “CI-level” tools. The triage doc already identifies invalid `w` / NaN as a plausible cause of scattered shadowing; implement explicit guards in shader so invalid coords become “lit” (or a debug color), never undefined sampling. fileciteturn34file0L1-L1 fileciteturn48file0L1-L1
- **Hard-disable bias in code** (not via CVars) for a diagnostic build: disable polygon offset and set receiver bias and PCF radius to zero in shader. If you still see detachment or scattering, you have proven it is not a tunable bias issue, confirming the triage thesis. fileciteturn34file0L1-L1
- **State validation around shadow passes**: log and assert FBO bindings, viewport/scissor state, depth mask, active texture unit, and bound textures for shadow samplers. The “unravelled” symptom is consistent with a viewport/scissor/FBO state leak or wrong binding that cannot be fixed by bias CVars. fileciteturn34file0L1-L1

Deliverable: a “shadow map validation mode” that makes it impossible for an incorrect map or incorrect coordinates to go unnoticed.

### Bias and filtering redesign for predictable contact fidelity

Once correctness is proven, redesign bias around predictable behavior and per-technique scaling.

- Treat **caster-side polygon offset** as a small stabilization tool, not the primary knob. Its behavior is defined and slope-dependent (`factor * DZ + r * units`), which is useful but also angle-sensitive. citeturn8search0turn8search7
- Keep **receiver bias** split into:
  - a small constant bias, and
  - a slope/normal term (already exposed through CVars). fileciteturn49file0L1-L1
- Add an optional **receiver-plane depth bias** mode for projected/CSM shadows when filter radius is large, following the guidance that derivative-based approaches can be necessary to avoid acne without inducing peter-panning under large PCF kernels. citeturn9search0
- Implement **per-cascade bias scaling**: cascades differ in texel footprint and depth distribution; a single bias set is rarely optimal across all cascades in practice.

Deliverable: default settings that minimize contact lift while remaining stable under motion, plus a structured bias tuning workflow tied to debug visualization.

### CSM hardening and quality upgrades

openQ4 already includes the right knobs for cascade count, split distribution (λ), blending, and stabilization. fileciteturn49file0L1-L1

To make CSM “production-grade”:

- Add an internal “fit mode” policy (conceptually similar to “fit to cascade vs fit to scene”), and ensure cascade bounds cannot become unstable on view/light movement. Microsoft’s doc shows how different fitting approaches trade wasted resolution vs stability artifacts. citeturn9search0
- Enforce **PCF guard bands**: either pad cascade rendering regions or clamp taps strictly. The Microsoft guidance explicitly calls out padding as a requirement for PCF kernels to avoid indexing outside partitions. citeturn9search0
- Add a per-light heuristic: if a light’s projective configuration produces unstable `w` / invalid projected regions frequently, automatically disable CSM for that light (fall back to single-map shadowing or even stencil, depending on quality target). This turns catastrophic artifacts into graceful degradation.

Deliverable: cascades that do not shimmer, do not leak across tiles, and that fail safe under degenerate projections.

### Transparency shadowing: finalize cutouts, formalize translucency

Cutouts are close to production-ready; translucency is not (by design).

- **Cutouts (hashed alpha)**:
  - Keep hashed alpha as default (it matches the modern reference that it prevents distant alpha-tested geometry disappearance at the cost of controlled noise). citeturn8search3
  - Add a “quality mode” that swaps the current hash for a higher-quality sampling pattern if desired (for example, blue-noise texture driven) while still keeping a stable domain. This should be optional because it adds texture bandwidth.
  - Validate that alpha-test thresholds and texture-coordinate transforms match real-world content expectations; your caster shader already supports alpha ref, alpha scale, and texture matrix rows. fileciteturn38file0L1-L1 fileciteturn39file0L1-L1

- **Blended/translucent moments**:
  - Either keep it clearly “experimental,” or align it with a proven moment-shadow-map formulation. The JCGT “Improved Moment Shadow Maps” paper is directly relevant for moment-based soft shadows and translucent occluders. citeturn9search36
  - If you keep your current approach, add strict “participation flags” (material keywords) so only vetted materials contribute, reducing surprise costs and artifacts.
  - Add “leak control” knobs (clamps, minimum variance, distribution guards) and clear warnings when the model becomes numerically ill-conditioned.

Deliverable: cutouts that look correct at all distances, and a translucency model that is either (a) formally grounded and defensible, or (b) explicitly scoped and safe.

### Performance policy and shadow budgeting

To make the system production-usable in real gameplay scenes:

- Add shadow-map budgeting: maximum shadowed lights per frame, maximum total shadow-map pixels per frame, and a priority ranking (on-screen influence, distance to camera, light type).
- For point lights (6 faces) and CSM (multiple cascades), allow **update rate throttling** for lights that are static relative to the world and camera.
- Add profiling counters: shadow map render time per light, total pixels rendered into shadow maps, and number of eligible translucent casters per light (since translucent moments add an extra pass). The docs already note the extra cost; production needs actual measurement hooks. fileciteturn49file0L1-L1

Deliverable: predictable frame time without disabling shadows globally.

### Test and QA harness for “no artifacts” readiness

Finally, bake correctness into a repeatable suite:

- A minimal “caster/receiver” test map: plane + box + a projected light with controllable pitch/yaw/roll; reproduce the angle-sensitive failures described in triage. fileciteturn34file0L1-L1
- A cutout test set: fences, grates, foliage cards at multiple distances; verify hashed alpha stability and that cutouts do not cast solid silhouettes. fileciteturn49file0L1-L1
- A CSM sweep: slow camera motion forward/back across cascade ranges with debug cascade-index overlay enabled; verify no shimmering, no seams, no tile leakage. fileciteturn48file0L1-L1
- A translucency test set (optional): only for explicitly supported translucent materials, validating that colored transmission is stable and not view-dependent (as documented), and that unsupported materials are safely excluded. fileciteturn49file0L1-L1

Deliverable: a “shadow correctness gate” you can run after any renderer change, ensuring the system remains configurable and artifact-free.

