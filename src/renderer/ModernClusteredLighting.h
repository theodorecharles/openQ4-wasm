// Copyright (C) 2004 Id Software, Inc.
//

#ifndef __MODERN_CLUSTERED_LIGHTING_H__
#define __MODERN_CLUSTERED_LIGHTING_H__

#include "RendererCaps.h"

class idScenePacketFrame;
typedef struct viewDef_s viewDef_t;

enum rendererClusterDebugMode_t {
	RENDERER_CLUSTER_DEBUG_OFF = 0,
	RENDERER_CLUSTER_DEBUG_OCCUPANCY,
	RENDERER_CLUSTER_DEBUG_LIGHT_COUNT,
	RENDERER_CLUSTER_DEBUG_OVERFLOW
};

enum rendererModernLightType_t {
	RENDERER_MODERN_LIGHT_POINT = 0,
	RENDERER_MODERN_LIGHT_PROJECTED,
	RENDERER_MODERN_LIGHT_FOG,
	RENDERER_MODERN_LIGHT_AMBIENT,
	RENDERER_MODERN_LIGHT_BLEND,
	RENDERER_MODERN_LIGHT_SPECIAL
};

static const int RENDERER_MODERN_SHADOW_DESCRIPTOR_MAX_TILES = 6;
static const int RENDERER_MODERN_SHADOW_DESCRIPTOR_MAX_CASCADES = 4;

enum rendererModernShadowDescriptorFlag_t {
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_MAPPED = 1 << 0,
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_CACHE_REUSE = 1 << 1,
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_STENCIL_FALLBACK = 1 << 2,
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_SKIPPED = 1 << 3,
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_RECEIVER_BLOCKED = 1 << 4,
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_PROJECTED = 1 << 5,
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_POINT = 1 << 6,
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_CASCADE = 1 << 7,
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_TRANSLUCENT = 1 << 8,
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_ATLAS_READY = 1 << 9,
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_CASTER_READY = 1 << 10,
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_RECEIVER_GUARD_READY = 1 << 11,
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_SAMPLING_READY = 1 << 12,
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_STABLE_CASCADE = 1 << 13,
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_PROJECTED_STATE_READY = 1 << 14,
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_PROJECTED_FALLBACK = 1 << 15,
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_RECEIVER_PLANE_BIAS = 1 << 16,
	// projectedAtlasRect references a live cell of ARB2's persistent shadow
	// atlas (signature-current, static content complete) - the only state in
	// which the modern receiver may sample a projected shadow
	RENDERER_MODERN_SHADOW_DESCRIPTOR_FLAG_ATLAS_SLOT = 1 << 17
};

typedef struct rendererModernShadowDescriptor_s {
	int		descriptorIndex;
	int		sceneIndex;
	int		lightDefIndex;
	int		mapType;
	int		policy;
	int		fallbackReason;
	int		compareMode;
	int		biasModel;
	int		depthFormat;
	int		pcfKernel;
	int		tileCount;
	int		cascadeCount;
	int		requestedCascadeCount;
	int		atlasDiv;
	int		faceIndex;
	int		cascadeIndex;
	int		projectedFallbackCascade;
	int		projectedFallbackReason;
	int		projectedSampleCount;
	int		projectedValidSampleCount;
	int		projectedSkippedSampleCount;
	int		flags;
	// freshness (I7): frame the planner built this descriptor, and the frame
	// the referenced atlas cell's static content was last rendered
	int		updateFrame;
	int		atlasContentFrame;
	int		atlasCellX;
	int		atlasCellY;
	int		atlasCellSpan;
	bool	atlasSlotValid;
	float	shadowMatrix[16];
	float	viewShadowMatrix[RENDERER_MODERN_SHADOW_DESCRIPTOR_MAX_CASCADES][16];
	float	projection[4];
	float	cascadeSplitDepths[RENDERER_MODERN_SHADOW_DESCRIPTOR_MAX_CASCADES];
	float	cascadeBiasScale[RENDERER_MODERN_SHADOW_DESCRIPTOR_MAX_CASCADES];
	float	texelDepthBias[RENDERER_MODERN_SHADOW_DESCRIPTOR_MAX_CASCADES];
	float	worldTexelSize[RENDERER_MODERN_SHADOW_DESCRIPTOR_MAX_CASCADES];
	float	sliceNear[RENDERER_MODERN_SHADOW_DESCRIPTOR_MAX_CASCADES];
	float	sliceFar[RENDERER_MODERN_SHADOW_DESCRIPTOR_MAX_CASCADES];
	float	depthRange[RENDERER_MODERN_SHADOW_DESCRIPTOR_MAX_CASCADES];
	float	clipZExtent[RENDERER_MODERN_SHADOW_DESCRIPTOR_MAX_CASCADES];
	float	bias[4];
	float	projectedBaseClipPlanes[4][4];
	float	projectedClipPlanes[RENDERER_MODERN_SHADOW_DESCRIPTOR_MAX_CASCADES][4][4];
	float	projectedAtlasRect[RENDERER_MODERN_SHADOW_DESCRIPTOR_MAX_CASCADES][4];
} rendererModernShadowDescriptor_t;

typedef struct rendererModernLightDescriptor_s {
	char	debugName[64];
	rendererModernLightType_t type;
	int		descriptorIndex;
	int		sceneIndex;
	int		lightDefIndex;
	int		areaNum;
	int		flags;
	int		shadowDescriptorIndex;
	int		shadowPolicy;
	int		shadowFallbackReason;
	bool	portalVisible;
	bool	fullDepthRange;
	float	worldOrigin[4];
	float	viewOriginRadius[4];
	float	color[4];
	float	scissorDepth[4];
	float	depthRange[4];
	float	falloff[4];
	float	projectS[4];
	float	projectT[4];
	float	projectQ[4];
	unsigned int projectionImageHandle;
	unsigned int falloffImageHandle;
	unsigned int cubeImageHandle;
	int		projectionFilter;
	int		projectionRepeat;
	int		falloffFilter;
	int		falloffRepeat;
} rendererModernLightDescriptor_t;

typedef struct rendererClusteredLightingStats_s {
	bool	available;
	bool	requested;
	bool	initialized;
	bool	frameValid;
	bool	buffersReady;
	bool	shadowDescriptorBufferReady;
	bool	uboFallbackReady;
	bool	debugOverlayReady;
	bool	debugTextureReady;
	bool	shaderStorageReady;
	bool	csrReady;
	bool	computeBinningReady;
	bool	computeBinningExecuted;
	bool	lossless;
	bool	overflow;
	int		gridCount;
	int		sceneCount;
	int		scenesWithLights;
	int		lightCount;
	int		pointLights;
	int		projectedLights;
	int		fogLights;
	int		ambientLights;
	int		blendLights;
	int		specialLights;
	int		shadowMappedLights;
	int		shadowFallbackLights;
	int		shadowSkippedLights;
	int		shadowDescriptorCount;
	int		uploadedShadowDescriptors;
	int		shadowDescriptorCapacity;
	int		shadowReceiverBlockedLights;
	int		shadowAtlasSlotBlockedLights;
	int		culledLights;
	int		clippedLights;
	int		overflowLights;
	int		clusterCount;
	int		activeClusters;
	int		overflowClusters;
	int		lightReferences;
	int		uploadedLights;
	int		uploadedClusters;
	int		uploadedReferences;
	int		spillClusters;
	int		spillReferences;
	int		unsampledSpillReferences;
	int		overflowReferences;
	int		lossyClusters;
	int		lossyReferences;
	int		maxLightsInCluster;
	int		maxLightsPerCluster;
	int		indexGroupsPerCluster;
	int		lightCapacity;
	int		indexRecordCapacity;
	int		clusterRecordCount;
	int		flatIndexRecordCount;
	int		flatIndexReferenceCapacity;
	int		uploadedGridIndexRecords;
	int		computeBinningDispatches;
	int		gridSwitches;
	int		gridBindFailures;
	int		tileCountX;
	int		tileCountY;
	int		sliceCountZ;
	int		nearZ;
	int		farZ;
	int		buildMsec;
	int		bufferUploads;
	int		paramsUBOBytes;
	int		lightsUBOBytes;
	int		indicesUBOBytes;
	int		shadowDescriptorBytes;
	int		debugMode;
	int		debugOverlayDraws;
	int		debugStringTruncations;
	char	debugStringTruncationSource[64];
	char	status[96];
} rendererClusteredLightingStats_t;

void R_ModernClusteredLighting_Init( const renderBackendCaps_t &caps, const renderFeatureSet_t &features );
void R_ModernClusteredLighting_Shutdown( void );
void R_ModernClusteredLighting_PrepareFrame( const idScenePacketFrame &packetFrame, bool requested );
void R_ModernClusteredLighting_DrawDebugOverlay( void );
void R_ModernClusteredLighting_PrintGfxInfo( void );
const rendererClusteredLightingStats_t &R_ModernClusteredLighting_Stats( void );
bool R_ModernClusteredLighting_FrameLossless( void );
bool R_ModernClusteredLighting_BindGridForView( const viewDef_t *viewDef );
int R_ModernClusteredLighting_NumLightDescriptors( void );
const rendererModernLightDescriptor_t *R_ModernClusteredLighting_LightDescriptor( int index );
int R_ModernClusteredLighting_NumShadowDescriptors( void );
const rendererModernShadowDescriptor_t *R_ModernClusteredLighting_ShadowDescriptor( int index );
// linked-size expectation for the shadow-descriptor UBO block, for std140
// layout-drift introspection against the driver (M5)
int R_ModernClusteredLighting_ShadowDescriptorUboBlockBytes( void );
bool RendererClusterGrid_RunSelfTest( void );

#endif /* !__MODERN_CLUSTERED_LIGHTING_H__ */
