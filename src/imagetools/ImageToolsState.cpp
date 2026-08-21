// Copyright (C) 2026 DarkMatter Productions
//

#include "ImageTools.h"
#include "../renderer/Image.h"		// textureFormat_t for BitsForFormat

/*
===============================================================================

	Library-owned state for the shared image utilities: static allocation
	(relocated from the renderer's tr_main.cpp) plus the renderer-pushed
	compression capabilities and allocation-counter hooks.

===============================================================================
*/

static imageToolsCompressionCaps_t it_compressionCaps;
static imageToolsAllocHooks_t it_allocHooks;

void ImageTools_SetCompressionCaps( const imageToolsCompressionCaps_t &caps ) {
	it_compressionCaps = caps;
}

const imageToolsCompressionCaps_t &ImageTools_GetCompressionCaps( void ) {
	return it_compressionCaps;
}

void ImageTools_SetStaticAllocHooks( const imageToolsAllocHooks_t &hooks ) {
	it_allocHooks = hooks;
}

/*
=================
R_StaticAlloc
=================
*/
void *R_StaticAlloc( size_t bytes ) {
	void	*buf;

	if ( it_allocHooks.onStaticAlloc != NULL ) {
		it_allocHooks.onStaticAlloc( bytes );
	}

	buf = Mem_Alloc( bytes );

	// don't exit on failure on zero length allocations since the old code didn't
	if ( !buf && ( bytes != 0 ) ) {
		common->FatalError( "R_StaticAlloc failed on %zu bytes", bytes );
	}
	return buf;
}

/*
=================
R_ClearedStaticAlloc
=================
*/
void *R_ClearedStaticAlloc( size_t bytes ) {
	void	*buf;

	buf = R_StaticAlloc( bytes );
	if ( buf != NULL ) {
		// Mem_Alloc rejects values above the legacy heap's signed 32-bit limit.
		SIMDProcessor->Memset( buf, 0, static_cast<int>( bytes ) );
	}
	return buf;
}

/*
=================
R_StaticFree
=================
*/
void R_StaticFree( void *data ) {
	if ( it_allocHooks.onStaticFree != NULL ) {
		it_allocHooks.onStaticFree();
	}
	Mem_Free( data );
}

/*
================
BitsForFormat

Relocated from the renderer in the Phase B closure: pure format math shared
by the binary-image codecs and the renderer modules.
================
*/
int BitsForFormat( textureFormat_t format ) {
	switch ( format ) {
		case FMT_NONE:		return 0;
		case FMT_RGBA8:		return 32;
		case FMT_XRGB8:		return 32;
		case FMT_RGBA16F:	return 64;
		case FMT_RGB565:	return 16;
		case FMT_L8A8:		return 16;
		case FMT_ALPHA:		return 8;
		case FMT_LUM8:		return 8;
		case FMT_INT8:		return 8;
		case FMT_DXT1:		return 4;
		case FMT_DXT5:		return 8;
		case FMT_BC7:		return 8;
		case FMT_DEPTH:		return 32;
		case FMT_DEPTH_STENCIL:	return 32;
		case FMT_X16:		return 16;
		case FMT_Y16_X16:	return 32;
		default:
			assert( 0 );
			return 0;
	}
}
