#!/usr/bin/env python3
"""Pin the committed Vulkan shader header to its GLSL sources.

The renderer-vk module embeds SPIR-V from a COMMITTED generated header so
builds never require glslang (CI runners carry no Vulkan SDK). When
glslangValidator IS available, this test regenerates the header and
byte-compares; when it is not, the test skips cleanly.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
GENERATOR = REPO_ROOT / "tools" / "build" / "spirv_to_header.py"
COMMITTED = REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "gui_shaders_spv.h"
SHADERS = [
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "gui.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "gui.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "screen.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "screen.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "sky.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "sky.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "environment.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "environment.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "bumpy_environment.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "bumpy_environment.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "heathaze.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "heathaze.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "heathaze_mask.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "heathaze_vertex.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "heathaze_mask_vertex.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "monochrome.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "monochrome.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "glasswarp.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "glasswarp.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_displacement.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_displacement.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_displacement_two_stage.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_displacement_two_stage.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_ghost_pulling.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_ghost_pulling.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_displacement2.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_displacement2.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_multiply_blend.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_multiply_blend.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_displacement_cube.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_displacement_cube.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_sniper_stretch2.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_sniper_stretch2.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_depth_texture.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_depth_texture.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_blur.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_blur.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_medlabs.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_medlabs.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_depth_texture2.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_depth_texture2.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_al.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_al.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_water.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_water.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "refractive_glass.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "refractive_glass.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_depth_aware_blur.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_depth_aware_blur.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_smaa_edge.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_smaa_edge.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_smaa_weights.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_smaa_weights.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_smaa_blend.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "material_smaa_blend.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "interaction.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "interaction.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "interaction_shadow.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "interaction_shadow.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "interaction_shadow_point.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "interaction_shadow_point.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "shadow_caster.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "shadow_caster.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "shadow_point_caster.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "shadow_point_caster.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "shadow_volume.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "shadow_volume.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "fog.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "fog.frag",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "blend_light.vert",
    REPO_ROOT / "src" / "renderer" / "Vulkan" / "shaders" / "blend_light.frag",
]


def main() -> int:
    sys.path.insert(0, str(GENERATOR.parent))
    import spirv_to_header  # noqa: E402

    if spirv_to_header.find_glslang(None) is None:
        print("vk_shader_header_pin: skipped (glslangValidator not available)")
        return 0

    if not COMMITTED.is_file():
        print(f"vk_shader_header_pin: missing committed header {COMMITTED}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        regenerated = pathlib.Path(tmp) / "gui_shaders_spv.h"
        result = subprocess.run(
            [
                sys.executable,
                str(GENERATOR),
                "--header-out",
                str(regenerated),
                *[str(s) for s in SHADERS],
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"vk_shader_header_pin: regeneration failed:\n{result.stdout}\n{result.stderr}", file=sys.stderr)
            return 1
        # EOL-insensitive: a fresh checkout can materialize the committed
        # header with LF while the generator writes platform line endings
        if regenerated.read_bytes().replace(b"\r\n", b"\n") != COMMITTED.read_bytes().replace(b"\r\n", b"\n"):
            shader_args = " ".join(s.relative_to(REPO_ROOT).as_posix() for s in SHADERS)
            print(
                "vk_shader_header_pin: committed header is stale — regenerate with:\n"
                "  python tools/build/spirv_to_header.py --header-out src/renderer/Vulkan/shaders/gui_shaders_spv.h "
                f"{shader_args}",
                file=sys.stderr,
            )
            return 1

    print("vk_shader_header_pin: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
