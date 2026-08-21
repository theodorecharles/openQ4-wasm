#version 450

// openQ4 Vulkan point-light shadow-map caster — vertex stage (Phase F2b,
// docs/dev/plans/2026-07-19-vulkan-phase-f.md).
//
// Depth-only caster into one face of a point light's depth cube, mirroring
// the GL shadow_point_caster.vs contract in its hardware-compare
// (OPENQ4_POINT_SHADOW_CASTER_DEPTH) variant: the map stores NORMALIZED
// RADIAL DISTANCE (length(worldPos - lightOrigin) / far), written by the
// fragment stage. The push mvp is the model -> cube-face VIEW matrix (not a
// clip transform): the face view is a rigid transform centered on the light
// origin, so the view-space position's length IS the world radial distance
// (exact even for scaled model matrices, matching the GL shader's
// world-space subtraction). The face projection is applied analytically:
// x' = x_eye, y' = y_eye, z' = zA*z_eye + zB*w_eye, w' = -z_eye — the GL
// RB_PointShadowMapBuildProjectionMatrix row passed through the shared
// VK_FixupClipSpaceZ convention.
//
// The push block keeps the shared 128B envelope. depthRow is free in the
// point variant (no depth plane): x,y carry the analytic projection row and
// z carries the far envelope. The alpha matrix rows' z components carry the
// two caster depth-offset scalars exactly like the projected caster.

layout(location = 0) in vec3 inPosition;
layout(location = 1) in vec2 inTexCoord;

layout(push_constant) uniform CasterPushConstants {
    mat4 mvp;        // model -> cube-face view space
    vec4 depthRow;   // x: zA, y: zB (clip z = zA*z_eye + zB*w_eye), z: far envelope
    vec4 alphaS;     // alpha-test texture matrix S row; z = slope-scale depth factor
    vec4 alphaT;     // alpha-test texture matrix T row; z = constant depth offset
    vec4 params;     // x: alpha mode, y: alphaRef, z: alphaScale, w: alpha-hash mode/seed
} pc;

layout(location = 0) out vec2 vAlphaTexCoord;
layout(location = 1) out vec3 vPointShadowVector;
layout(location = 2) out vec3 vAlphaHashCoord;

void main() {
    vec4 position = vec4(inPosition, 1.0);
    vec4 texCoord = vec4(inTexCoord, 0.0, 1.0);
    // texCoord.z is 0, so the depth-offset scalars packed into the matrix
    // rows' z components never contribute to the texture coordinate
    vAlphaTexCoord = vec2(dot(texCoord, pc.alphaS), dot(texCoord, pc.alphaT));
    vec4 viewPos = pc.mvp * position;
    vPointShadowVector = viewPos.xyz;
    // Shared across all six faces, unlike face-view coordinates.
    vAlphaHashCoord = inPosition;
    gl_Position = vec4(viewPos.xy, pc.depthRow.x * viewPos.z + pc.depthRow.y * viewPos.w, -viewPos.z);
}
