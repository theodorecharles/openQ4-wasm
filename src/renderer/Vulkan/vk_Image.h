// Copyright (C) 2026 DarkMatter Productions
//

#ifndef __VK_IMAGE_H__
#define __VK_IMAGE_H__

/*
===============================================================================

	Vulkan idImage backing (Phase D). texnum indexes the module-side image
	table; the executor caches descriptors keyed on the generation counter.

===============================================================================
*/

#include "volk.h"

struct VmaAllocation_T;
typedef struct VmaAllocation_T *VmaAllocation;

typedef struct vkImageEntry_s {
	bool			inUse;
	VkImage			image;
	VmaAllocation	allocation;
	VkImageView		view;
	// Depth/stencil images need a depth-only sampled view and a combined
	// depth+stencil attachment view. Color and depth-only images alias this
	// to view.
	VkImageView		attachmentView;
	VkSampler		sampler;
	VkFormat		format;
	VkImageUsageFlags usage;
	VkImageAspectFlags aspectMask;
	VkImageLayout	layout;
	VkSampleCountFlagBits samples;
	int				width;
	int				height;
	int				numMips;
	int				numLayers;		// 6 for cube maps
	bool			isCube;
	bool			everUploaded;	// first upload transitions from UNDEFINED
	// generation counter for executor-side descriptor caching
	unsigned int	generation;
} vkImageEntry_t;

static const int VK_MAX_IMAGES = 4096;

vkImageEntry_t *VK_Image_GetEntry( unsigned int texnum );
// Re-backs an idImage with exact-format, single-sample depth storage suitable
// for vkCmdCopyImage feedback captures while keeping the idImage's public
// dimensions in sync with the copied region.
bool	VK_Image_MakeDepthCopyTarget( idImage *image, int width, int height,
			VkFormat depthFormat );
void	VK_Image_ShutdownAll( void );

#endif /* !__VK_IMAGE_H__ */
