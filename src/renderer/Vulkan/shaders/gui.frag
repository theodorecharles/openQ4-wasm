#version 450

// openQ4 Vulkan GUI/2D pipeline — fragment stage (Phase D,
// docs/dev/plans/2026-07-18-vulkan-phase-d.md).
//
// One combined image sampler; component swizzles (fonts' green-alpha,
// R8-backed alpha/intensity formats) live on the VkImageView, so the
// sample here is already in canonical RGBA space.

layout(binding = 0) uniform sampler2D texSampler;

layout(location = 0) in vec2 fragTexCoord;
layout(location = 1) in vec4 fragColor;

layout(push_constant) uniform GuiPushConstants {
    mat4 mvp;
    vec4 stageColor;
    vec4 texMatrixS;
    vec4 texMatrixT;
    vec4 params;
} pc;

layout(location = 0) out vec4 outColor;

void main() {
    vec4 color = texture(texSampler, fragTexCoord) * fragColor;
    if (pc.params.y > 0.5) {
        if (pc.params.y > 1.5) {
            if (abs(color.a - pc.params.z) > (0.5 / 255.0)) {
                discard;
            }
        } else if (color.a <= pc.params.z) {
            discard;
        }
    } else if (pc.params.y < -0.5 && color.a >= pc.params.z) {
        discard;
    }
    outColor = color;
}
