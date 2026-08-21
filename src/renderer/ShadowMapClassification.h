// Copyright (C) 2004 Id Software, Inc.
//

#ifndef __SHADOWMAP_CLASSIFICATION_H__
#define __SHADOWMAP_CLASSIFICATION_H__

typedef struct viewLight_s viewLight_t;

static const int SHADOWMAP_CLASSIFICATION_MAX_CASCADES = 4;

typedef enum {
	SHADOWMAP_LIGHT_PROJECTED = 0,
	SHADOWMAP_LIGHT_POINT,
	SHADOWMAP_LIGHT_PARALLEL,
	SHADOWMAP_LIGHT_GLOBAL
} shadowMapLightClass_t;

typedef struct shadowMapLightClassification_s {
	shadowMapLightClass_t	lightClass;
	bool					projectedLight;
	bool					pointLight;
	bool					ordinaryProjectedLight;
	bool					parallelLight;
	bool					globalLight;
	bool					projectedCSMGateApplies;
	bool					projectedCSMEnabled;
	bool					csmEnabled;
	int						cascadeCount;
	int						atlasDiv;
	int						tileCount;
} shadowMapLightClassification_t;

// Receiver filtering is expressed in shadow texels, but a texel from a
// parallel/global (sky) projection covers substantially more world space than
// one from a local projector.  Keep the source-aware policy in one place so
// the cascade fitter, legacy receiver, and modern descriptor agree.
typedef struct shadowMapProjectedFilterSettings_s {
	bool					distantSource;
	float				filterScale;
	float				filterRadius;
	int					filterTaps;
	int					filterMode;
	float				pcssLightRadius;
	float				pcssMaxRadius;
	float				effectiveFilterRadius;
} shadowMapProjectedFilterSettings_t;

shadowMapLightClassification_t R_ClassifyShadowMapLight( const viewLight_t *vLight );
shadowMapProjectedFilterSettings_t R_ShadowMapProjectedFilterSettings( const viewLight_t *vLight );
const char *R_ShadowMapLightClassName( shadowMapLightClass_t lightClass );

#endif /* !__SHADOWMAP_CLASSIFICATION_H__ */
