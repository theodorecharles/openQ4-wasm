#version 450

// openQ4 Vulkan interaction pipeline — vertex stage (Phase F1,
// docs/dev/plans/2026-07-19-vulkan-phase-f.md).
//
// Per-light bump/diffuse/specular interaction, mirroring the stock Quake 4
// interaction.vfp semantics (material_interaction.vs is the GLSL reference).
// Consumes the full idDrawVert; the per-draw interaction block streams
// through a dynamic uniform ring on set 6 (296B of per-draw data overflows
// the 128B push floor). The push-constant block keeps the shared 128B shape
// {mat4; vec4 a,b,c,d} so every pipeline layout carries the same range:
//   a.x = vertex-color modulate, a.y = vertex-color add (SVC packing),
//   a.z = ambient light flag; b.xyz = the tangent-space ambient light
//   direction exactly as the ambient normal-map cube decodes it;
//   c.xy = custom-lighting parallax scale/bias, c.z = parallax enable.

layout(location = 0) in vec3 inPosition;
layout(location = 1) in vec4 inColor;
layout(location = 2) in vec3 inNormal;
layout(location = 3) in vec3 inTangent0;
layout(location = 4) in vec3 inTangent1;
layout(location = 5) in vec2 inTexCoord;

layout(push_constant) uniform InteractionPushConstants {
    mat4 mvp;
    vec4 a;
    vec4 b;
    vec4 c;
    vec4 d;
} pc;

layout(set = 6, binding = 0, std140) uniform InteractionBlock {
    vec4 localLightOrigin;
    vec4 localViewOrigin;
    vec4 lightProjectionS;
    vec4 lightProjectionT;
    vec4 lightProjectionQ;
    vec4 lightFalloffS;
    vec4 bumpMatrixS;
    vec4 bumpMatrixT;
    vec4 diffuseMatrixS;
    vec4 diffuseMatrixT;
    vec4 specularMatrixS;
    vec4 specularMatrixT;
    vec4 diffuseColor;
    vec4 specularColor;
    vec4 flatDiffuseParams;
} inter;

layout(location = 0) out vec2 vBumpTexCoord;
layout(location = 1) out vec2 vDiffuseTexCoord;
layout(location = 2) out vec2 vSpecularTexCoord;
layout(location = 3) out vec4 vLightFalloffTexCoord;
layout(location = 4) out vec4 vLightProjectionTexCoord;
layout(location = 5) out vec3 vLightVector;
layout(location = 6) out vec3 vHalfAngleVector;
layout(location = 7) out vec3 vVertexColor;
layout(location = 8) out vec3 vViewVector;

vec3 TangentSpaceVector(vec3 objectVector) {
    return vec3(
        dot(inTangent0, objectVector),
        dot(inTangent1, objectVector),
        dot(inNormal, objectVector));
}

void main() {
    vec4 position = vec4(inPosition, 1.0);
    vec4 texCoord = vec4(inTexCoord, 0.0, 1.0);

    vec3 toLight = inter.localLightOrigin.xyz - position.xyz;
    vec3 toView = inter.localViewOrigin.xyz - position.xyz;

    vLightVector = TangentSpaceVector(toLight);
    vHalfAngleVector = TangentSpaceVector(normalize(toLight) + normalize(toView));
    vViewVector = TangentSpaceVector(toView);

    vBumpTexCoord = vec2(dot(texCoord, inter.bumpMatrixS), dot(texCoord, inter.bumpMatrixT));
    vDiffuseTexCoord = vec2(dot(texCoord, inter.diffuseMatrixS), dot(texCoord, inter.diffuseMatrixT));
    vSpecularTexCoord = vec2(dot(texCoord, inter.specularMatrixS), dot(texCoord, inter.specularMatrixT));

    // z is unused by textureProj for this 2D sampler; carry model-local Z.
    vLightFalloffTexCoord = vec4(dot(position, inter.lightFalloffS), 0.5, position.z, 1.0);
    vLightProjectionTexCoord = vec4(
        dot(position, inter.lightProjectionS),
        dot(position, inter.lightProjectionT),
        0.0,
        dot(position, inter.lightProjectionQ));

    vVertexColor = inColor.rgb * pc.a.x + vec3(pc.a.y);

    gl_Position = pc.mvp * position;
}
