#version 450

// openQ4 Vulkan stencil shadow volume — fragment stage (Phase G1).
//
// The volume pipeline masks every color write (colorWriteMask 0) and only
// the depth test + stencil ops matter; this stage exists because the
// shared pipeline assembly always carries two stages.

void main() {
}
