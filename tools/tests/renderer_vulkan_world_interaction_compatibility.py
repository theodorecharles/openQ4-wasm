#!/usr/bin/env python3
"""Regression contracts for Vulkan world-light interaction parity."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEST_PATH = "tools/tests/renderer_vulkan_world_interaction_compatibility.py"


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def compact(value: str) -> str:
    return " ".join(value.split())


def require(haystack: str, needle: str, context: str) -> None:
    if needle not in haystack:
        raise AssertionError(f"Missing {needle!r} in {context}")


def require_compact(haystack: str, needle: str, context: str) -> None:
    if compact(needle) not in compact(haystack):
        raise AssertionError(
            f"Missing compact source contract {compact(needle)!r} in {context}"
        )


def require_order(haystack: str, needles: tuple[str, ...], context: str) -> None:
    compact_haystack = compact(haystack)
    previous = -1
    for needle in needles:
        position = compact_haystack.find(compact(needle), previous + 1)
        if position == -1:
            raise AssertionError(f"Missing {compact(needle)!r} in {context}")
        if position <= previous:
            raise AssertionError(f"Expected ordered contracts in {context}: {needles!r}")
        previous = position


def braced_body(source: str, marker: str, context: str) -> str:
    start = source.find(marker)
    if start == -1:
        raise AssertionError(f"Missing {marker!r} in {context}")
    opening_brace = source.find("{", start + len(marker))
    if opening_brace == -1:
        raise AssertionError(f"Missing opening brace after {marker!r} in {context}")

    depth = 0
    for index in range(opening_brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"Could not find closing brace for {marker!r} in {context}")


def validate_stock_bump_sampling_contract() -> None:
    image_source = read("src/renderer/Vulkan/vk_Image.cpp")
    format_info = braced_body(
        image_source,
        "static bool VK_Image_GetFormatInfo(",
        "Vulkan image-format selection",
    )
    require_order(
        format_info,
        (
            "else if ( usage == TD_BUMP && opts.colorFormat != CFM_NORMAL_DXT5 )",
            "info.swizzle.a = VK_COMPONENT_SWIZZLE_R;",
        ),
        "Quake 4 bump red-to-alpha texture view",
    )

    fragment = read("src/renderer/Vulkan/shaders/interaction.frag")
    require_order(
        fragment,
        (
            "vec4 bumpSample = texture(bumpMap, bumpTexCoord);",
            "vec3 localNormal = vec3(bumpSample.a, bumpSample.g, bumpSample.b)",
            "float ndotl = max(dot(lightDir, localNormal), 0.0);",
            "float specularTerm = texture(specularTableMap",
            "vec3 specular = texture(specularMap",
            "outColor = vec4((diffuse + specular) * light * vVertexColor, 0.0);",
        ),
        "stock interaction fragment math",
    )


def validate_interaction_decomposition() -> None:
    source = read("src/renderer/Vulkan/vk_Interactions.cpp")
    create = braced_body(
        source,
        "static void VK_CreateSingleDrawInteractions(",
        "Vulkan primitive interaction decomposition",
    )
    require_order(
        create,
        (
            "r_skipInteractions.GetBool()",
            "VK_Exec_BindTriGeometry(",
            "VK_Exec_SetSurfScissor(",
            "surfaceShader->GetCullType()",
            "surfaceShader->TestMaterialFlag( MF_POLYGONOFFSET )",
            "R_GlobalPointToLocal(",
            "R_GlobalPlaneToLocal(",
            "if ( !lightRegs[ lightStage->conditionRegister ] )",
            "RB_BakeTextureMatrixIntoTexgen(",
            "case SL_BUMP:",
            "VK_SubmitInteraction( &inter );",
            "case SL_DIFFUSE:",
            "case SL_SPECULAR:",
            "VK_SubmitInteraction( &inter );",
            "VK_DrawCustomLightingStage(",
            "vkCmdSetDepthBiasEnable( interPass.cmd, VK_FALSE );",
        ),
        "Vulkan primitive interaction decomposition",
    )
    for token in (
        "surfaceRegs[ surfaceStage->conditionRegister ]",
        "surfaceStage->vertexColor",
        "backEnd.lightScale",
        "lightStage->color.registers",
        "inter.ambientLight = lightShader->IsAmbientLight()",
    ):
        require(create, token, "Vulkan primitive interaction decomposition")

    submit = braced_body(
        source,
        "static void VK_SubmitInteraction(",
        "stock interaction submission",
    )
    for token in (
        "r_skipDiffuse.GetBool()",
        "r_skipSpecular.GetBool()",
        "din->ambientLight",
        "r_skipBump.GetBool()",
        "globalImages->blackImage",
        "globalImages->flatNormalMap",
        "VK_DrawSingleInteraction( din )",
    ):
        require(submit, token, "stock interaction debug substitutions")

    custom_submit = braced_body(
        source,
        "static void VK_SubmitCustomLightingInteraction(",
        "customLighting submission",
    )
    for forbidden in ("r_skipDiffuse", "r_skipSpecular", "r_skipBump"):
        if forbidden in custom_submit:
            raise AssertionError(
                f"Raven customLighting stages must retain authored maps under {forbidden}"
            )
    require(
        custom_submit,
        "VK_DrawSingleInteractionMode( din, parallax, scaleBias[ 0 ], scaleBias[ 1 ] );",
        "customLighting direct interaction submission",
    )

    custom_stage = braced_body(
        source,
        "static void VK_DrawCustomLightingStage(",
        "customLighting stage translation",
    )
    for token in (
        "VK_GLSL_PROGRAM_FAMILY_CUSTOM_LIT",
        "VK_GLSL_PROGRAM_FAMILY_PARALLAX_BUMP",
        '"NormalMap"',
        '"DiffuseMap"',
        '"SpecularMap"',
        '"LightFalloffImage"',
        '"LightImage"',
        "surfaceRegs[ surfaceStage->conditionRegister ]",
        "VK_CustomLightingScaleBias(",
        "VK_SubmitCustomLightingInteraction(",
    ):
        require(custom_stage, token, "customLighting stage translation")


def validate_light_ownership_and_draw_state() -> None:
    source = read("src/renderer/Vulkan/vk_Interactions.cpp")
    draw_lights = braced_body(
        source,
        "void VK_Interactions_DrawLights(",
        "Vulkan world-light loop",
    )
    for token in (
        "vLight->lightShader->IsFogLight()",
        "vLight->lightShader->IsBlendLight()",
        "VK_SHADOW_RECEIVER_LOCAL",
        "VK_SHADOW_RECEIVER_GLOBAL",
        "vLight->globalShadows",
        "vLight->localShadows",
        "vLight->globalShadowMapStencilSupplements",
        "vLight->localShadowMapStencilSupplements",
        "vLight->localInteractions",
        "vLight->globalInteractions",
        "vLight->translucentInteractions",
        "VK_COMPARE_OP_EQUAL",
        "VK_COMPARE_OP_LESS_OR_EQUAL",
        "r_skipTranslucent.GetBool()",
        "r_shadowMapTranslucentReceivers.GetBool()",
        "r_stencilTranslucentShadows.GetBool()",
        "required shadow resource unavailable; affected light receivers are skipped fail-closed",
    ):
        require(draw_lights, token, "Vulkan world-light ownership and draw state")
    require_order(
        draw_lights,
        (
            "VK_StencilShadowPass( localGlobalVolumes );",
            "VK_DrawInteractionChain( vLight->localInteractions );",
            "VK_StencilShadowPass( globalGlobalVolumes );",
            "VK_StencilShadowPass( globalLocalVolumes );",
            "VK_DrawInteractionChain( vLight->globalInteractions );",
        ),
        "retail and hybrid stencil ownership order",
    )

    executor = read("src/renderer/Vulkan/vk_GuiExecutor.cpp")
    interaction_pipeline = braced_body(
        executor,
        "VkPipeline VK_Exec_InteractionPipeline(",
        "Vulkan interaction pipeline",
    )
    require(
        interaction_pipeline,
        "GLS_SRCBLEND_ONE | GLS_DSTBLEND_ONE",
        "ONE:ONE additive interaction blend",
    )


def validate_scissor_and_depth_bounds_state() -> None:
    executor = read("src/renderer/Vulkan/vk_GuiExecutor.cpp")
    scissor = braced_body(
        executor,
        "void VK_Exec_SetSurfScissor(",
        "Vulkan interaction scissor",
    )
    require_compact(
        scissor,
        """( r_useScissor.GetBool() && !drawSurf->scissorRect.IsEmpty() )
            ? drawSurf->scissorRect : viewDef->scissor""",
        "surface/view scissor selection",
    )
    for token in ("viewDef->viewport", "fbHeight", "vkCmdSetScissor"):
        require(scissor, token, "bounded Vulkan interaction scissor")

    interactions = read("src/renderer/Vulkan/vk_Interactions.cpp")
    stencil_clear = braced_body(
        interactions,
        "static void VK_Inter_StencilClear(",
        "per-light stencil clear",
    )
    require_compact(
        stencil_clear,
        """const idScreenRect &rect = r_useScissor.GetBool()
            ? vLight->scissorRect : viewDef->scissor;""",
        "light/view stencil-clear selection",
    )

    device = read("src/renderer/Vulkan/VulkanDevice.cpp")
    for token in (
        "features2.features.depthBounds = supported.depthBounds;",
        "vkCtx.depthBoundsSupported = supported.depthBounds == VK_TRUE;",
        "Vulkan: optional depth features clamp=%d bounds=%d",
    ):
        require(device, token, "optional depth-bounds feature enablement")

    create_pipeline = braced_body(
        executor,
        "static VkPipeline VK_Exec_CreatePipeline(",
        "Vulkan dynamic pipeline state",
    )
    for token in (
        "VK_DYNAMIC_STATE_DEPTH_BOUNDS_TEST_ENABLE",
        "VK_DYNAMIC_STATE_DEPTH_BOUNDS",
    ):
        require(create_pipeline, token, "Vulkan dynamic depth-bounds state")

    stencil_pass = braced_body(
        interactions,
        "static bool VK_StencilShadowPass(",
        "Vulkan stencil shadow pass",
    )
    require_order(
        stencil_pass,
        (
            "vkCmdSetDepthBoundsTestEnable( cmd, VK_TRUE );",
            "vkCmdSetDepthBounds( cmd, minDepth, maxDepth );",
            "vkCmdSetDepthBoundsTestEnable( cmd, VK_FALSE );",
            "vkCmdSetDepthBounds( cmd, 0.0f, 1.0f );",
        ),
        "stencil shadow depth-bounds lifetime",
    )


def validate_ci_registration() -> None:
    validator = read("tools/validation/openq4_validate.py")
    commit = read(".github/workflows/commit-validation.yml")
    push = read(".github/workflows/push-verification.yml")

    if validator.count("renderer_vulkan_world_interaction_compatibility.py") != 1:
        raise AssertionError(
            "Local validation must register the Vulkan world-interaction test exactly once"
        )
    for workflow, context in (
        (commit, "commit validation workflow"),
        (push, "push verification workflow"),
    ):
        if workflow.count(TEST_PATH) != 2:
            raise AssertionError(f"{context} must compile and directly run {TEST_PATH}")
        require(workflow, f"python {TEST_PATH}", context)


def main() -> None:
    validate_stock_bump_sampling_contract()
    validate_interaction_decomposition()
    validate_light_ownership_and_draw_state()
    validate_scissor_and_depth_bounds_state()
    validate_ci_registration()
    print("renderer_vulkan_world_interaction_compatibility: ok")


if __name__ == "__main__":
    main()
