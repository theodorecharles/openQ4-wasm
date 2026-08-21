# Vendored Vulkan Memory Allocator (VMA)

- Source: Vulkan SDK 1.4.313.1 (VulkanMemoryAllocator, AMD)
- License: MIT (see file banner)
- Header-only; the implementation is compiled in
  `src/renderer/Vulkan/VulkanVmaImpl.cpp` with
  `VMA_STATIC_VULKAN_FUNCTIONS=0` / `VMA_DYNAMIC_VULKAN_FUNCTIONS=1`
  (function pointers supplied by Volk).
- Update together with `src/external/vulkan` from the same SDK.
