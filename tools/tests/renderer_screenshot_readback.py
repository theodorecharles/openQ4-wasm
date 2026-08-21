#!/usr/bin/env python3
"""Regression contract for composited-window screenshot readback."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def require(source: str, snippet: str, context: str) -> None:
    if snippet not in source:
        raise AssertionError(f"Missing {snippet!r} in {context}")


def require_order(source: str, snippets: tuple[str, ...], context: str) -> None:
    positions = [source.find(snippet) for snippet in snippets]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise AssertionError(f"Expected ordered snippets in {context}: {snippets!r}")


def test_screenshot_reads_the_unpresented_back_buffer() -> None:
    init_cpp = read("src/renderer/RenderSystem_init.cpp")
    require_order(
        init_cpp,
        (
            "session->UpdateScreen();",
            "glReadBuffer( r_frontBuffer.GetBool() ? GL_FRONT : GL_BACK );",
            "glReadPixels( 0, 0, w, h, GL_RGB, GL_UNSIGNED_BYTE, temp );",
        ),
        "regular screenshot readback path",
    )


def test_capture_defers_only_the_window_present() -> None:
    backend_cpp = read("src/renderer/tr_backend.cpp")
    require_order(
        backend_cpp,
        (
            "RB_ApplyResolutionScaleToBackBuffer();",
            "RB_ApplyCRTToBackBuffer();",
            "RB_ApplyColorMappingsToBackBuffer();",
            "if ( !r_frontBuffer.GetBool() && !tr.takingScreenshot )",
            "GLimp_SwapBuffers();",
        ),
        "RB_SwapBuffers screenshot presentation gate",
    )


def test_vulkan_capture_resumes_the_acquired_back_buffer() -> None:
    backend_cpp = read("src/renderer/Vulkan/vk_Backend.cpp")
    executor_cpp = read("src/renderer/Vulkan/vk_GuiExecutor.cpp")
    require(
        backend_cpp,
        "if ( !tr.takingScreenshot )",
        "Vulkan swap-buffer screenshot presentation gate",
    )
    read_pixels_start = executor_cpp.index("bool VK_GuiExecutor_ReadPixels")
    submit_start = executor_cpp.index("static bool VK_GuiExecutor_SubmitFrame", read_pixels_start)
    require_order(
        executor_cpp[read_pixels_start:submit_start],
        (
            "const bool resumeAfterReadback = tr.takingScreenshot;",
            "VK_GuiExecutor_SubmitFrame( !resumeAfterReadback )",
            "VK_Exec_BeginMainRendering( true );",
        ),
        "Vulkan screenshot readback resume path",
    )


def main() -> None:
    test_screenshot_reads_the_unpresented_back_buffer()
    test_capture_defers_only_the_window_present()
    test_vulkan_capture_resumes_the_acquired_back_buffer()
    print("renderer_screenshot_readback: ok")


if __name__ == "__main__":
    main()
