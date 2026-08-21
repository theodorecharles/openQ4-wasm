#version 450

// openQ4 Vulkan shadow-receiving interaction — fragment stage (Phase F2a).
//
// interaction.frag plus the projected shadow sample of the GL
// shadow_interaction.fs projected CSM contract: view-depth cascade selection
// and split-band blending over one contiguous per-light atlas block. Set 7
// exposes both a LEQUAL comparison sampler and an unfiltered raw-depth
// sampler, allowing the archived r_shadowMapDepthCompare preference and
// PCSS-lite blocker search without pipeline variants. Fixed/rotated Poisson
// modes use the stock 1/5/9/13 tap tiers; receiver-plane derivatives and the
// source-aware radius policy are supplied through the 512-byte shadow ABI.
// The shadow coordinate projects like the GL shader: xy/w for tile-local UV,
// z UNdivided as compare depth. Out-of-frustum receivers stay lit.

layout(set = 0, binding = 0) uniform sampler2D specularTableMap;
layout(set = 1, binding = 0) uniform sampler2D bumpMap;
layout(set = 2, binding = 0) uniform sampler2D lightFalloffMap;
layout(set = 3, binding = 0) uniform sampler2D lightProjectionMap;
layout(set = 4, binding = 0) uniform sampler2D diffuseMap;
layout(set = 5, binding = 0) uniform sampler2D specularMap;
layout(set = 7, binding = 0) uniform sampler2DShadow shadowCompareMap;
layout(set = 7, binding = 2) uniform sampler2D shadowRawMap;

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

layout(set = 7, binding = 1, std140) uniform ShadowBlock {
    vec4 shadowRow0[4];
    vec4 shadowRow1[4];
    vec4 shadowRow2[4];
    vec4 shadowRow3[4];
    vec4 atlasRects[4];
    vec4 splitDepths;
    vec4 cascadeBiasScale;
    vec4 texelDepthBias;
    vec4 normalOffsetWorld;
    vec4 viewDepthRow;
    vec4 biasParams;   // x: constant bias, y: normal bias, z: cascade blend, w: cascade count
    vec4 texelSize;    // x,y: 1 / atlas dimensions
    vec4 filterParams; // x: radius, y: taps, z: mode, w: hardware compare
    vec4 pcssParams;   // x: light radius, y: max radius, z: effective radius, w: receiver-plane bias
} shadow;

layout(location = 0) in vec2 vBumpTexCoord;
layout(location = 1) in vec2 vDiffuseTexCoord;
layout(location = 2) in vec2 vSpecularTexCoord;
layout(location = 3) in vec4 vLightFalloffTexCoord;
layout(location = 4) in vec4 vLightProjectionTexCoord;
layout(location = 5) in vec3 vLightVector;
layout(location = 6) in vec3 vHalfAngleVector;
layout(location = 7) in vec3 vVertexColor;
layout(location = 8) in vec4 vShadowCoord0;
layout(location = 9) in vec4 vShadowCoord1;
layout(location = 10) in vec4 vShadowCoord2;
layout(location = 11) in vec4 vShadowCoord3;
layout(location = 12) in float vShadowLightCos;
layout(location = 13) in vec3 vViewVector;
layout(location = 14) in float vViewDepth;

layout(location = 0) out vec4 outColor;

// Computed in main before any divergent receiver control flow. Derivatives
// inside the cascade selector would be undefined for neighboring fragments
// that choose different cascades.
vec4 gShadowDepthGradients = vec4(0.0);

vec3 SafeNormalize(vec3 value) {
    return value * inversesqrt(max(dot(value, value), 1.0e-8));
}

vec3 ApplyFlatDiffuseSweep(vec3 diffuse, float localZ) {
    if (inter.flatDiffuseParams.x <= 0.0) {
        return diffuse;
    }
    float height = clamp((localZ - inter.flatDiffuseParams.y)
        * inter.flatDiffuseParams.z, 0.0, 1.0);
    float distanceToBand = abs(height - fract(inter.flatDiffuseParams.w));
    distanceToBand = min(distanceToBand, 1.0 - distanceToBand);
    float band = 1.0 - smoothstep(0.045, 0.16, distanceToBand);
    return mix(diffuse, vec3(1.0), inter.flatDiffuseParams.x * band);
}

int ShadowCascadeCount() {
    return clamp(int(shadow.biasParams.w + 0.5), 1, 4);
}

float CascadeComponent(vec4 values, int cascadeIndex) {
    return values[clamp(cascadeIndex, 0, 3)];
}

vec4 ShadowCoordByIndex(int cascadeIndex) {
    if (cascadeIndex <= 0) {
        return vShadowCoord0;
    }
    if (cascadeIndex == 1) {
        return vShadowCoord1;
    }
    if (cascadeIndex == 2) {
        return vShadowCoord2;
    }
    return vShadowCoord3;
}

vec4 AtlasRectByIndex(int cascadeIndex) {
    if (cascadeIndex <= 0) {
        return shadow.atlasRects[0];
    }
    if (cascadeIndex == 1) {
        return shadow.atlasRects[1];
    }
    if (cascadeIndex == 2) {
        return shadow.atlasRects[2];
    }
    return shadow.atlasRects[3];
}

float StableShadowHash(vec3 value) {
    return fract(sin(dot(value, vec3(12.9898, 78.233, 37.719)))
        * 43758.5453);
}

vec2 RotateShadowOffset(vec2 offset, vec2 uv, float depth) {
    if (shadow.filterParams.z < 0.5) {
        return offset;
    }
    float angle = StableShadowHash(vec3(
        floor(uv / max(shadow.texelSize.x, 1.0e-6)),
        floor(depth * 1024.0))) * 6.2831853;
    float s = sin(angle);
    float c = cos(angle);
    return vec2(c * offset.x - s * offset.y,
        s * offset.x + c * offset.y);
}

float ShadowDepthGradient(int cascadeIndex) {
    return CascadeComponent(gShadowDepthGradients, cascadeIndex);
}

float ShadowReceiverBias(int cascadeIndex) {
    float lightCos = clamp(vShadowLightCos, 0.20, 1.0);
    float sinTheta = sqrt(max(1.0 - lightCos * lightCos, 0.0));
    float slopeBias = min(sinTheta / lightCos, 4.0);
    float scalarBias = (shadow.biasParams.x
        + shadow.biasParams.y * sinTheta)
        * CascadeComponent(shadow.cascadeBiasScale, cascadeIndex);
    float texelBias = CascadeComponent(shadow.texelDepthBias,
        cascadeIndex) * (1.0 + slopeBias);
    float receiverPlaneBias = 0.0;
    if (shadow.pcssParams.w > 0.5) {
        receiverPlaneBias = ShadowDepthGradient(cascadeIndex)
            * max(shadow.pcssParams.z, 1.0);
    }
    return max(max(scalarBias, 0.0),
        max(max(texelBias, receiverPlaneBias), 0.0));
}

float SampleShadowCompare(vec2 uv, float depth, int cascadeIndex) {
    float compareDepth = depth - ShadowReceiverBias(cascadeIndex);
    if (shadow.filterParams.w > 0.5) {
        return texture(shadowCompareMap, vec3(uv, compareDepth));
    }
    float storedDepth = texture(shadowRawMap, uv).r;
    return compareDepth <= storedDepth ? 1.0 : 0.0;
}

float RawShadowDepth(vec2 uv) {
    return texture(shadowRawMap, uv).r;
}

float ProjectedPCSSRadius(vec2 uv, float depth, int cascadeIndex,
        vec2 clampMin, vec2 clampMax, vec2 texelStep) {
    float baseRadius = shadow.filterParams.x;
    if (shadow.filterParams.z < 1.5 || shadow.filterParams.w > 0.5
            || shadow.pcssParams.x <= 0.0
            || shadow.pcssParams.y <= 0.0) {
        return baseRadius;
    }

    float compareDepth = depth - ShadowReceiverBias(cascadeIndex);
    vec2 searchTap = texelStep * max(shadow.pcssParams.x, 0.5);
    float blockerDepth = 0.0;
    float blockerCount = 0.0;
    float d0 = RawShadowDepth(uv);
    if (d0 < compareDepth) {
        blockerDepth += d0;
        blockerCount += 1.0;
    }
    vec2 o1 = RotateShadowOffset(vec2(-0.5, -0.5), uv, depth);
    vec2 o2 = RotateShadowOffset(vec2(0.5, -0.5), uv, depth);
    vec2 o3 = RotateShadowOffset(vec2(-0.5, 0.5), uv, depth);
    vec2 o4 = RotateShadowOffset(vec2(0.5, 0.5), uv, depth);
    float d1 = RawShadowDepth(clamp(uv + o1 * searchTap,
        clampMin, clampMax));
    float d2 = RawShadowDepth(clamp(uv + o2 * searchTap,
        clampMin, clampMax));
    float d3 = RawShadowDepth(clamp(uv + o3 * searchTap,
        clampMin, clampMax));
    float d4 = RawShadowDepth(clamp(uv + o4 * searchTap,
        clampMin, clampMax));
    if (d1 < compareDepth) { blockerDepth += d1; blockerCount += 1.0; }
    if (d2 < compareDepth) { blockerDepth += d2; blockerCount += 1.0; }
    if (d3 < compareDepth) { blockerDepth += d3; blockerCount += 1.0; }
    if (d4 < compareDepth) { blockerDepth += d4; blockerCount += 1.0; }
    if (blockerCount <= 0.0) {
        return baseRadius;
    }

    float averageBlocker = blockerDepth / blockerCount;
    float penumbra = (depth - averageBlocker)
        / max(averageBlocker, 1.0e-4);
    float maxRadius = max(baseRadius, shadow.pcssParams.y);
    return clamp(max(baseRadius, penumbra * shadow.pcssParams.x),
        baseRadius, maxRadius);
}

float SampleShadowCascade(vec4 shadowCoord, vec4 atlasRect,
        int cascadeIndex) {
    float w = shadowCoord.w;
    // !(w > eps) also rejects NaN.
    if (!(w > 1.0e-5) || w > 65536.0) {
        return 1.0;
    }

    vec2 projectedXY = shadowCoord.xy / w;
    float depth = shadowCoord.z;
    vec3 projected = vec3(projectedXY, depth);
    if (any(isnan(projected)) || any(isinf(projected))
            || any(greaterThan(abs(projected), vec3(65536.0)))) {
        return 1.0;
    }
    vec2 localUv = projectedXY * 0.5 + 0.5;
    if (localUv.x <= 0.0 || localUv.x >= 1.0
            || localUv.y <= 0.0 || localUv.y >= 1.0) {
        return 1.0;
    }
    if (depth <= 0.0 || depth >= 1.0) {
        return 1.0;
    }

    vec2 uv = mix(atlasRect.xy, atlasRect.zw, localUv);
    // The composed rect's v span is inverted (Vulkan y-down atlas rows).
    // Keep Poisson offsets in tile-local orientation while clamping with
    // component-wise rect bounds.
    vec2 rectMin = min(atlasRect.xy, atlasRect.zw);
    vec2 rectMax = max(atlasRect.xy, atlasRect.zw);
    vec2 texelStep = shadow.texelSize.xy
        * sign(atlasRect.zw - atlasRect.xy);
    float guardRadius = max(0.5, shadow.pcssParams.z + 0.75);
    vec2 guardBand = abs(shadow.texelSize.xy) * guardRadius;
    vec2 clampMin = rectMin + guardBand;
    vec2 clampMax = rectMax - guardBand;
    clampMin = min(clampMin, clampMax);
    uv = clamp(uv, clampMin, clampMax);

    float filterRadius = ProjectedPCSSRadius(uv, depth, cascadeIndex,
        clampMin, clampMax, texelStep);
    if (filterRadius <= 0.0) {
        return SampleShadowCompare(uv, depth, cascadeIndex);
    }

    vec2 tap = texelStep * filterRadius;
    float result = SampleShadowCompare(uv, depth, cascadeIndex);
    if (shadow.filterParams.y <= 1.0) {
        return result;
    }
    vec2 o1 = RotateShadowOffset(vec2(-0.326212, -0.405805), uv, depth);
    vec2 o2 = RotateShadowOffset(vec2(-0.840144, -0.073580), uv, depth);
    vec2 o3 = RotateShadowOffset(vec2(-0.695914, 0.457137), uv, depth);
    vec2 o4 = RotateShadowOffset(vec2(-0.203345, 0.620716), uv, depth);
    result += SampleShadowCompare(clamp(uv + o1 * tap,
        clampMin, clampMax), depth, cascadeIndex);
    result += SampleShadowCompare(clamp(uv + o2 * tap,
        clampMin, clampMax), depth, cascadeIndex);
    result += SampleShadowCompare(clamp(uv + o3 * tap,
        clampMin, clampMax), depth, cascadeIndex);
    result += SampleShadowCompare(clamp(uv + o4 * tap,
        clampMin, clampMax), depth, cascadeIndex);
    if (shadow.filterParams.y <= 5.0) {
        return result * (1.0 / 5.0);
    }
    vec2 o5 = RotateShadowOffset(vec2(0.962340, -0.194983), uv, depth);
    vec2 o6 = RotateShadowOffset(vec2(0.473434, -0.480026), uv, depth);
    vec2 o7 = RotateShadowOffset(vec2(0.519456, 0.767022), uv, depth);
    vec2 o8 = RotateShadowOffset(vec2(0.185461, -0.893124), uv, depth);
    result += SampleShadowCompare(clamp(uv + o5 * tap,
        clampMin, clampMax), depth, cascadeIndex);
    result += SampleShadowCompare(clamp(uv + o6 * tap,
        clampMin, clampMax), depth, cascadeIndex);
    result += SampleShadowCompare(clamp(uv + o7 * tap,
        clampMin, clampMax), depth, cascadeIndex);
    result += SampleShadowCompare(clamp(uv + o8 * tap,
        clampMin, clampMax), depth, cascadeIndex);
    if (shadow.filterParams.y <= 9.0) {
        return result * (1.0 / 9.0);
    }
    vec2 o9 = RotateShadowOffset(vec2(0.507431, 0.064425), uv, depth);
    vec2 o10 = RotateShadowOffset(vec2(0.896420, 0.412458), uv, depth);
    vec2 o11 = RotateShadowOffset(vec2(-0.321940, -0.932615), uv, depth);
    vec2 o12 = RotateShadowOffset(vec2(-0.791559, -0.597705), uv, depth);
    result += SampleShadowCompare(clamp(uv + o9 * tap,
        clampMin, clampMax), depth, cascadeIndex);
    result += SampleShadowCompare(clamp(uv + o10 * tap,
        clampMin, clampMax), depth, cascadeIndex);
    result += SampleShadowCompare(clamp(uv + o11 * tap,
        clampMin, clampMax), depth, cascadeIndex);
    result += SampleShadowCompare(clamp(uv + o12 * tap,
        clampMin, clampMax), depth, cascadeIndex);
    return result * (1.0 / 13.0);
}

int SelectShadowCascade(float viewDepth) {
    int interiorSplitCount = ShadowCascadeCount() - 1;
    if (interiorSplitCount <= 0 || viewDepth < shadow.splitDepths.x) {
        return 0;
    }
    if (interiorSplitCount <= 1 || viewDepth < shadow.splitDepths.y) {
        return 1;
    }
    if (interiorSplitCount <= 2 || viewDepth < shadow.splitDepths.z) {
        return 2;
    }
    return 3;
}

float SampleCascadeByIndex(int cascadeIndex) {
    return SampleShadowCascade(ShadowCoordByIndex(cascadeIndex),
        AtlasRectByIndex(cascadeIndex), cascadeIndex);
}

float SampleShadowFactor() {
    int cascadeIndex = SelectShadowCascade(vViewDepth);
    float shadowFactor = SampleCascadeByIndex(cascadeIndex);
    int lastInteriorIndex = ShadowCascadeCount() - 2;
    float cascadeBlend = shadow.biasParams.z;
    if (cascadeIndex > lastInteriorIndex || cascadeBlend <= 0.0) {
        return shadowFactor;
    }

    float previousSplit = cascadeIndex == 0 ? 0.0
        : CascadeComponent(shadow.splitDepths, cascadeIndex - 1);
    float currentSplit = CascadeComponent(shadow.splitDepths, cascadeIndex);
    float blendWidth = max(1.0,
        (currentSplit - previousSplit) * cascadeBlend);
    float blendStart = currentSplit - blendWidth;
    if (vViewDepth <= blendStart) {
        return shadowFactor;
    }

    float blend = clamp((vViewDepth - blendStart) / blendWidth, 0.0, 1.0);
    if (blend <= 0.02) {
        return shadowFactor;
    }
    return mix(shadowFactor, SampleCascadeByIndex(cascadeIndex + 1),
        blend);
}

void main() {
    if (shadow.pcssParams.w > 0.5) {
        gShadowDepthGradients = vec4(
            abs(dFdx(vShadowCoord0.z)) + abs(dFdy(vShadowCoord0.z)),
            abs(dFdx(vShadowCoord1.z)) + abs(dFdy(vShadowCoord1.z)),
            abs(dFdx(vShadowCoord2.z)) + abs(dFdy(vShadowCoord2.z)),
            abs(dFdx(vShadowCoord3.z)) + abs(dFdy(vShadowCoord3.z)));
    }

    vec2 bumpTexCoord = vBumpTexCoord;
    vec2 diffuseTexCoord = vDiffuseTexCoord;
    vec2 specularTexCoord = vSpecularTexCoord;
    if (pc.c.z > 0.5) {
        float height = texture(bumpMap, bumpTexCoord).r;
        vec2 offset = SafeNormalize(vViewVector).xy * (height * pc.c.x + pc.c.y);
        bumpTexCoord += offset;
        diffuseTexCoord += offset;
        specularTexCoord += offset;
    }

    vec4 bumpSample = texture(bumpMap, bumpTexCoord);
    vec3 localNormal = vec3(bumpSample.a, bumpSample.g, bumpSample.b) * 2.0 - 1.0;

    vec3 lightDir = (pc.a.z > 0.5) ? pc.b.xyz : SafeNormalize(vLightVector);
    float ndotl = max(dot(lightDir, localNormal), 0.0);

    vec3 light = vec3(ndotl);
    light *= textureProj(lightFalloffMap, vLightFalloffTexCoord).rgb;
    light *= textureProj(lightProjectionMap, vLightProjectionTexCoord).rgb;
    light *= SampleShadowFactor();

    vec3 diffuse = texture(diffuseMap, diffuseTexCoord).rgb * inter.diffuseColor.rgb;
    diffuse = ApplyFlatDiffuseSweep(diffuse, vLightFalloffTexCoord.z);

    vec3 halfAngle = SafeNormalize(vHalfAngleVector);
    float specularDot = clamp(dot(halfAngle, localNormal), 0.0, 1.0);
    float specularTerm = texture(specularTableMap, vec2(specularDot, 0.5)).r * 2.0;
    vec3 specular = texture(specularMap, specularTexCoord).rgb * inter.specularColor.rgb * specularTerm;

    outColor = vec4((diffuse + specular) * light * vVertexColor, 0.0);
}
