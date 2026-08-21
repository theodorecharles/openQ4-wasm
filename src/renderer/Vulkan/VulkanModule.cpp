// Copyright (C) 2026 DarkMatter Productions
//

/*
===============================================================================

	renderer-vk backend tail (Phase C,
	docs/dev/plans/2026-07-17-vulkan-phase-c.md).

	The shared module glue (RendererGLModule.cpp under OPENQ4_RENDERER_MODULE)
	owns the GetRenderAPI export and the engine-interface binding; this TU
	supplies the Vulkan-specific pieces the glue attaches: the bring-up
	diagnostics surface for the on-demand rendererVkProbe flow and the
	services handoff for the probe path.

===============================================================================
*/

#ifdef OPENQ4_RENDERER_VK_MODULE

#include "../../idlib/precompiled.h"
#pragma hdrstop

#include "../RenderModuleAPI.h"
#include "VulkanBringup.h"

static const renderModuleDiagnostics_t vk_moduleDiagnostics = {
	VK_Bringup_RunProbe,
	VK_Bringup_RunDeviceSelfTest,
};

const renderModuleDiagnostics_t *VK_GetModuleDiagnostics( void ) {
	return &vk_moduleDiagnostics;
}

/*
====================
VK_ModuleBindServices

Called by the shared glue after the import handshake so the bring-up /
diagnostics layer can print through the engine.
====================
*/
void VK_ModuleBindServices( const renderModuleServices_t *services ) {
	VK_Bringup_SetServices( services );
}

#endif /* OPENQ4_RENDERER_VK_MODULE */
