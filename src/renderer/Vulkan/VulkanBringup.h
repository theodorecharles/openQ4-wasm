// Copyright (C) 2026 DarkMatter Productions
//

#ifndef __VULKANBRINGUP_H__
#define __VULKANBRINGUP_H__

/*
===============================================================================

	Vulkan renderer module bring-up diagnostics (roadmap Phase A).

	Instance/device/queue/memory validation with no window or surface work,
	safe to run while the OpenGL renderer owns the screen. Later phases grow
	this module toward the full idRenderSystem implementation described in
	docs/dev/plans/2026-07-16-vulkan-renderer.md.

	This translation unit is standalone: no idlib, engine services arrive
	through the renderModuleServices_t table.

===============================================================================
*/

struct renderModuleServices_s;

void	VK_Bringup_SetServices( const struct renderModuleServices_s *services );

// full bring-up pass: loader -> instance (+ optional validation) -> device
// enumeration/selection -> logical device + queues -> VMA allocations ->
// timeline semaphore -> teardown; reports through services->Printf
bool	VK_Bringup_RunProbe( bool verbose );

// quiet pass/fail wrapper for self-test harnesses
bool	VK_Bringup_RunDeviceSelfTest( char *outSummary, int summaryLength );

// releases any cached module state; called before the engine unloads the module
void	VK_Bringup_Shutdown( void );

#endif /* !__VULKANBRINGUP_H__ */
