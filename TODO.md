# openQ4 TODO

This file tracks current known issues and upcoming features.

## Known Issues

- [x] Viewport sometimes remains black when changing between SP and MP; investigate update/refresh logic during module transitions.
- [ ] Menu cursor handling needs improvement (focus, capture, and consistency across input modes and resolutions).
- [x] The locked door/scripted trigger progression bug inherited from Quake4Doom was fixed by porting OpenD3's x64 script-compiler pointer-temp storage guard (4-byte object-ref temp vs 8-byte pointer temp mismatch).
- [ ] Machinegun zoom projection yaw differs from viewangles yaw.

## Upcoming Features and Improvements

- [ ] Native Vulkan renderer with full OpenGL parity behind dynamic renderer modules and `r_renderApi` — phased roadmap in [docs/dev/plans/2026-07-16-vulkan-renderer.md](docs/dev/plans/2026-07-16-vulkan-renderer.md); Phase A (module ABI, loader, fail-closed fallback, `renderer-vk` bring-up diagnostics) is in place.
- [ ] Add an optional shadow mapping setting/path.
- [ ] Review and port relevant features and improvements implemented in the last 5 years of RBDOOM3-BFG commits.
- [ ] Merge shared code between MP/SP and streamline the process of switching between each.
- [ ] Find and implement ways to improve loading times.
- [ ] Expand multiplayer controls and port relevant WORR functionality/logic.
- [ ] Improve menu and loading screen horizontal expansion behavior.
- [ ] Machinegun and railgun zoom images need to suit all screen aspect ratios.
- [ ] CPMA-esque rainbow a-z color escapes implementation, disable black

## Potential change in project scope

Project may benefit from catering towards multiple idTech4 titles, to include: Doom 3, Doom 3: BFG, Prey, ETQW
