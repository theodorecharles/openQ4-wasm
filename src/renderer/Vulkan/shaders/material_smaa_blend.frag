#version 450

// Vulkan port of openQ4's live smaa_blend.fs material program.

layout(set = 0, binding = 0) uniform sampler2D ColorTex;
layout(set = 1, binding = 0) uniform sampler2D BlendTex;

layout(set = 6, binding = 0, std140) uniform MaterialShaderParms {
    vec4 shaderParms[16];
} material;

layout(location = 0) in vec2 vTexCoord;
layout(location = 0) out vec4 outColor;

void main() {
    vec2 invTexSize = material.shaderParms[0].xy;
    vec2 texcoord = vTexCoord;

    vec4 a;
    a.x = texture(BlendTex, texcoord + vec2(invTexSize.x, 0.0)).a;
    a.y = texture(BlendTex, texcoord + vec2(0.0, invTexSize.y)).g;
    a.wz = texture(BlendTex, texcoord).xz;

    if (dot(a, vec4(1.0)) < 0.00001) {
        outColor = texture(ColorTex, texcoord);
        return;
    }

    bool horizontal = max(a.x, a.z) > max(a.y, a.w);
    vec4 blendingOffset = vec4(0.0, a.y, 0.0, a.w);
    vec2 blendingWeight = a.yw;
    if (horizontal) {
        blendingOffset = vec4(a.x, 0.0, a.z, 0.0);
        blendingWeight = a.xz;
    }

    blendingWeight /= max(dot(blendingWeight, vec2(1.0)), 0.00001);
    vec4 blendingCoord =
        blendingOffset * vec4(invTexSize, -invTexSize) + texcoord.xyxy;
    vec4 color =
        blendingWeight.x * texture(ColorTex, blendingCoord.xy);
    color += blendingWeight.y * texture(ColorTex, blendingCoord.zw);
    outColor = color;
}
