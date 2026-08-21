// Copyright (C) 2004 Id Software, Inc.
//

#ifndef __SHADOWMAP_ARB2_PARITY_H__
#define __SHADOWMAP_ARB2_PARITY_H__

#include "ShadowMapProjected.h"

typedef struct shadowMapArb2ParityState_s {
	bool							valid;
	bool							pointLight;
	bool							projectedLight;
	bool							csmEnabled;
	int								requestedCascadeCount;
	int								cascadeCount;
	int								tileCount;
	int								atlasDiv;
	int								tileSize;
	bool							projectedStateReady;
	bool							projectedCascadeFallback;
	int								projectedFallbackCascade;
	shadowMapProjectedLightState_t	projectedState;
} shadowMapArb2ParityState_t;

enum shadowMapArb2CachePassMask_t {
	SHADOWMAP_ARB2_CACHE_PASS_LOCAL = 1u << 0,
	SHADOWMAP_ARB2_CACHE_PASS_GLOBAL = 1u << 1
};

typedef struct shadowMapArb2CacheEstimate_s {
	bool							valid;
	bool							pointLight;
	bool							staticCacheEnabled;
	int								lightIndex;
	int								shadowPasses;
	int								cacheablePasses;
	int								cacheHitPasses;
	int								cacheMissPasses;
	int								freshUpdatePasses;
	int								budgetFallbackPasses;
	int								stencilOnlyPasses;
	int								receiverFallbackPasses;
	int								unshadowedPasses;
	unsigned int					cacheablePassMask;
	unsigned int					cacheHitPassMask;
	unsigned int					cacheMissPassMask;
	unsigned int					freshUpdatePassMask;
	unsigned int					budgetFallbackPassMask;
	int								projectedCacheSlotsUsed;
	int								projectedCacheSlotsTotal;
	int								pointCacheSlotsUsed;
	int								pointCacheSlotsTotal;
} shadowMapArb2CacheEstimate_t;

// A cached projected light's placement inside the persistent shadow atlas.
// cascadeAtlasRect is composed into PERSISTENT-ATLAS UV space (min/max per
// cascade) with the same math the ARB2 receiver upload uses, so a consumer
// can sample the atlas texture directly. Atlas cells hold STATIC content
// only: lights with dynamic casters get those composed over scratch per
// frame, which the atlas cell does not contain.
typedef struct shadowMapArb2AtlasSlot_s {
	bool	valid;
	int		lightIndex;
	int		signature;
	int		cellX;
	int		cellY;
	int		cellSpan;
	int		cellSizePixels;
	int		atlasWidthPixels;
	int		atlasHeightPixels;
	int		tileSize;
	int		atlasDiv;
	int		cascadeCount;
	int		lastUpdatedFrame;
	int		lastUsedFrame;
	float	cascadeAtlasRect[SHADOWMAP_PROJECTED_MAX_CASCADES][4];
} shadowMapArb2AtlasSlot_t;

bool RB_ShadowMapBuildArb2ParityState( const viewLight_t *vLight, const viewDef_t *viewDef, int shadowMapSize, shadowMapArb2ParityState_t &state );
bool RB_ShadowMapEstimateArb2CacheOwnership( const viewLight_t *vLight, const viewDef_t *viewDef, shadowMapArb2CacheEstimate_t &estimate );
bool RB_ShadowMapProjectedAtlasSlotForLight( int lightDefIndex, shadowMapArb2AtlasSlot_t &slot );
void RB_ShadowMapProjectedAtlasSlotMarkUsed( int lightDefIndex );
bool RB_ShadowMapArb2ReceiverFallbackSelfTest( void );

#endif /* !__SHADOWMAP_ARB2_PARITY_H__ */
