# TrueType font system

openQ4 can render GUI text from scalable TrueType faces instead of the retail
Quake 4 bitmap atlases. This document covers both halves: the generator that
builds the font files, and the engine path that draws with them.

This is the **default** path as of this release. `r_useTrueTypeFonts 0` returns
to the bitmap atlases, byte-for-byte unchanged, and is the fallback whenever the
`.ttf` files are absent.

## Why

The retail fonts are fixed 12/24/48 point atlases drawn onto a 640x480 virtual
canvas. Every display above that resolution scales the atlas up, so text gets
softer the higher the display resolution goes — at 1440p the 48 point atlas is
being magnified 3x. The TrueType path rasterises the same letterforms at the
resolution the display actually uses, so text stays crisp.

## The font files

`content/baseoq4/pak0/fonts/*.ttf` — one face per retail bitmap font:

| File | Family | Notes |
| --- | --- | --- |
| `chain.ttf` | openQ4 Chain | Wide squarish techno sans; the default UI face |
| `lowpixel.ttf` | openQ4 LowPixel | Neo-grotesque, used for dense HUD readouts |
| `marine.ttf` | openQ4 Marine | All caps; radio and objective text |
| `profont.ttf` | openQ4 ProFont | Rounded technical face |
| `r_strogg.ttf` | openQ4 Roman Strogg | Angular oblique Strogg-Roman |
| `strogg.ttf` | openQ4 Strogg | Alien runes; Latin only by design |
| `bigchars.ttf` | openQ4 BigChars | Console and loading screen; monospaced, traced from the fixed-cell sheet |

Every face except `strogg` maps roughly 2,950 codepoints: ASCII, Latin-1, Latin
Extended-A/B, Vietnamese, Greek, Cyrillic, Arabic (including the
Presentation Forms-B joined shapes), Hebrew, punctuation, currency, arrows and
geometric shapes. `strogg.ttf` deliberately covers only the Latin runes it was
drawn for, folding accented letters onto their base rune.

## Generator

`tools/assets/fonts/` rebuilds the whole set from an installed copy of the game.

```bash
python tools/assets/fonts/extract_source_fonts.py --install "C:/Program Files (x86)/Steam/steamapps/common/Quake 4/q4base" --output .tmp/fontsrc
```

```bash
python tools/assets/fonts/build_openq4_fonts.py --source .tmp/fontsrc --donors .tmp/fontdonors --output content/baseoq4/pak0/fonts
```

The donor directory needs `NotoSans-var.ttf`, `NotoSansArabic-var.ttf` and
`NotoSansHebrew-var.ttf` from the Google Fonts repository, alongside their
`OFL.txt`.

### Pipeline

1. **Trace.** The 48 point atlas is the highest-fidelity source. Marching squares
   recovers the 50% iso-contour, but the crossing position is computed from the
   coverage value itself rather than by interpolating between two samples — a
   coverage sample *is* the exact area of a unit pixel inside the glyph, so it
   localises the edge directly. Interpolating against a saturated neighbour
   biases every edge outward by up to ~0.08px, which shows up as a halo.
2. **Corner detection and run fitting.** The contour is split at genuine corners,
   and each stretch between two corners is classified as a whole. Straightness is
   judged as a ratio of run length, not an absolute distance: a 30px stem edge
   drifts ~0.008 of its length while a 36 degree arc bulges ~0.08 of its chord,
   so the two never overlap.
3. **Axis snapping.** Near-axis lines are forced onto the axis and their offsets
   clustered, so both edges of a stem share one coordinate. Adjacent straight
   runs are intersected to restore corners the antialiasing rounded off.
4. **Composition.** Diacritics are lifted out of the retail precomposed glyphs
   (the acute out of `Á`, the cedilla out of `Ç`, and so on), and caron, macron,
   dot-above and double-acute are derived from those. Latin Extended-A/B and
   Vietnamese are then built as base plus mark, so they are authentic Quake 4
   shapes rather than imports.
5. **Shape sharing.** Cyrillic and Greek letters that are identical to a Latin
   one — А В Е К М Н О Р С Т Х, Α Β Ε Ζ Η Ι Κ Μ Ν Ο Ρ Τ Υ Χ and the lowercase
   equivalents — reuse the traced Quake 4 outline, so most of any Cyrillic or
   Greek run stays in the real face. Cyrillic PE and U are *not* shared: PE is a
   pi shape, not an N, and both cases of U carry a descending tail.
6. **Donors.** Whatever is left comes from Noto. Because the donors are variable
   fonts, each one is instantiated at the weight and width whose stem-to-cap
   ratio already matches the target face, rather than being distorted after the
   fact. The solved instances differ per face — Chain lands on 737/88, ProFont on
   450/85 — which is what keeps the imported scripts at the right colour.
7. **Synthesis.** Noto Sans carries almost nothing from the arrows, geometric and
   misc-symbol blocks, so those are constructed directly at the face's weight.

Small sources get an extra step first. Step 1 places an edge from the coverage
value itself, treating a sample as the area of a pixel cut by *one* edge. That
holds at 48 point, where a stem spans several pixels, but not on the 16 pixel
console cells, where a single pixel is usually cut by both sides of a stem at
once — there the assumption breaks down and contours come out lumpy, with
counters closing up and `@` collapsing into a blob. Any source below
`DENSIFY_TARGET_SIZE` (64px) is therefore resampled up to roughly that size
before tracing, which separates the two edges into different pixels and restores
the assumption. Bilinear is the right reconstruction: the sheet is antialiased,
so the coverage ramp already encodes where the edge sits. On `bigchars` this
takes mean coverage error from 0.044 to 0.036 and IoU from 0.913 to 0.931. The
resample is itself a low-pass, so contour smoothing is switched off when it runs
— smoothing again only rounds off detail the source had.

### Fidelity

The generator scores every traced glyph by rasterising it and comparing against
the retail coverage it models. Across the six faces the mean absolute coverage
error is 0.4–0.8% with total area within 0.3% of the source, which means the
outlines reproduce the originals rather than merely resembling them.

### A defect in the retail data

`chain`'s space glyph has a **zero advance** in all three retail point sizes,
which collapses every gap in a line of text drawn in that face. Every other face
uses exactly half an em. The generator substitutes half an em and reports
`space_repaired=1`. This is a deliberate divergence from the shipped data: text
drawn in `chain` will be spaced differently under `r_useTrueTypeFonts 1` than it
is under `0`.

## Engine

- `src/renderer/TrueType.h/.cpp` — a self-contained TrueType reader and
  rasteriser. It handles `glyf` outlines (simple and composite), format 4 and 12
  character maps, horizontal metrics and legacy `kern` pairs. There is no
  third-party dependency: the project keeps its dependency surface small, and a
  font file is untrusted input that is easier to bounds-check in-tree. Every
  read goes through a range-checked reader, so a truncated or hostile file
  yields zeroes rather than reading past the end.
  The rasteriser accumulates exact per-pixel signed area per edge and integrates
  along each scanline, so coverage is analytically correct without supersampling.
- `src/renderer/tr_fontTTF.cpp` — rasterises codepoints 32–255 for each of the
  three point sizes, packs them into a glyph atlas and fills the same
  `fontInfo_t` the bitmap loader produces. Because the metric units and UV
  conventions are identical, nothing downstream needs to know which path
  produced the font, and `fontInfo_t`'s layout is untouched (it is mirrored into
  `openQ4-game`).

The atlas is rasterised at the display's own upscale factor
(`displayHeight / 480`), clamped to 6x. Atlas pages are RGBA8 with white colour
and coverage in alpha, matching the retail atlases so the GUI blend path is
unchanged. Each glyph gets a transparent gutter wide enough to absorb the
bleed guard `DeviceContext` applies when sampling.

### Matching the bitmap fonts' size

The point of the exercise is text that is *sharper*, not text that is bigger,
smaller or differently spaced, so the sizing is held to the retail atlases in
two separate places.

**The ink.** Measured against the retail coverage, traced glyph extents land
within a few percent of the atlas they model across all six faces and all three
point sizes — the residual is the retail bitmap's own texel quantisation, which
is 4 visual units per texel at 12 point. Advances are exact: every printable
ASCII codepoint in every face reproduces the retail advance to the unit, so a
string occupies the same width either way. The single exception is `chain`'s
space, covered above.

**The rect.** A retail `.fontdat` records each glyph as its ink plus a one texel
border on every side, and one retail texel is one metric unit. The GUI reads
those rects back as `glyph.width`/`glyph.height`, and they are not merely the
drawn quad: `DrawText` derives its line spacing from `maxHeight`, the character
cell it fits text into from `maxWidth`, and `TextHeight` from the tallest glyph
in the string. So the border has to be one *metric unit*, which is `upscale`
texels here, not the one texel the rasteriser leaves. Reporting the rasteriser's
border instead makes the metrics shrink as the rasterisation scale rises — the
same font reports a different cell at 1080p and at 1440p — and put GUI text a
few pixels above where the bitmap path puts it. The atlas gutter covers this
border as well as the bleed guard.

`maxWidth`/`maxHeight` also skip the Windows-1252 punctuation band, 0x80–0x9F.
The retail atlases leave much of it blank — `chain` and `profont` carry an empty
2x2 rect for the florin, per mille, em dash and ellipsis, and `chain` gives them
a zero advance as well — so the generator fills those slots from a donor face.
Those donor glyphs are wider and taller than anything the retail font could
draw: letting the per mille sign set `profont`'s layout cell inflated it by 62%.
Measuring the repertoire the GUIs were authored against brings both extents to
within 6% of retail for every face and size at 1080p and above, tightening as
resolution rises. What is left is the rasteriser rounding the ink out to whole
texels, which is the same quantisation the retail bitmaps carry.

Two size divergences are left on purpose. `chain`'s repaired space makes any
string containing one about 10% wider than the retail atlas draws it, which is
the point of the repair. And the faces declare real `ascender`/`descender`
values where several retail fonts declare wrong ones — `marine` reports a font
height 66% larger — which is harmless because GUI layout reads neither field;
see the text-background section for what does use them.

That display height comes from **`glConfig`, not `engineWindowState`**. The
latter is the engine-owned window mirror the module polls at present time: at
font-registration time it still holds the pre-mode logical window size, and its
UI viewport is never populated on this path at all. Reading it produced an
upscale of 1.5 on a 1440p display instead of 3.0, so every atlas was rasterised
at half the resolution the display needed and text stayed softer than it should
have been.

Font atlases follow the renderer restart lifecycle. A full `vid_restart`
releases cached TrueType faces before image purge, reallocates persistent atlas
images with the new context, reinitialises the font reader, and immediately
rebuilds the console sheet. A successful partial restart keeps the context,
faces, and images alive, but still refreshes the resolution-dependent console
sheet. Cached GUI fonts notice the renderer restart generation on their next
lookup or selection and re-register in place, preserving the integer indices
stored by parsed GUIs as well as the active font and size selection.

Glyph area grows with the square of the scale, so a slot is capped at
`Q4_TTF_MAX_PAGE_AREA` (2048x2048, 16MB at RGBA8). The required area is
predicted from the glyph metrics, which needs no rasterising, and the slot's
scale is pulled back if it would not fit. The clamp only engages above 1440p,
where 3x is already past the point of visible return. A face at full resolution
costs roughly 16MB + 4MB + 1MB across its three sizes; `r_ttfFontResolution`
scales that quadratically for anyone who wants the memory back.

### The console sheet

The console and the loading screen never went through the font system: they
slice characters straight out of `bigchars`, a 16x16 grid of 16x16 pixel cells
indexed by byte, which is why console text was the blurriest text in the game.

`R_BuildConsoleFontAtlas` rebuilds that sheet at display resolution - same grid,
same cell indexing, just larger cells - and retargets the existing
`fonts/english/bigchars` material at it. Because the UV maths in
`Con_DrawSizedChar` is purely fractional (`0.0625` per cell), every caller keeps
working with no change to `Console.cpp` or `Common.cpp`, and no new renderer
interface. Glyphs are clipped to their own cell so nothing can bleed into a
neighbour.

`bigchars.ttf` is traced from that 16px sheet rather than borrowed from another
face - the closest existing face, `lowpixel`, scores a 0.16 shape difference
against it, which is nowhere near a match. Tracing 16px cells is inherently
coarser than the 48pt sources, but the sheet is genuinely antialiased (174
distinct coverage levels), so the sub-pixel edge localisation has real signal to
work with and the result is a clean vector rather than a magnified block.

It carries the same extended coverage as the other faces, and its advances are
forced to one em. The source is a fixed-cell font and both consumers step a
fixed cell per character, ignoring font advances entirely, so a proportional
advance would be fiction — which is what the donor-imported scripts arrive
carrying. Note that the console still indexes by byte, so the extended coverage
is present in the file but not reachable from the console itself.

### Cvars

| Cvar | Default | Meaning |
| --- | --- | --- |
| `r_useTrueTypeFonts` | `1` | Draw GUI text from the `.ttf` faces |
| `r_ttfFontResolution` | `1.0` | Multiplier on atlas rasterisation resolution |
| `r_ttfFontDebug` | `0` | Dump each atlas to `fs_savepath/ttfatlas` and log its layout |

Changing `r_useTrueTypeFonts` takes effect the next time fonts are registered.

`uiFontParitySelfTest` asserts parity with the retail atlases — exact advances,
and that the radio font resolves to the marine atlas material. Those cases are
skipped when the TrueType path is active, since measuring a deliberately
different rasteriser against the retail one is a category error rather than a
regression. `tools/tests/renderer_validation_matrix.py` pins
`r_useTrueTypeFonts 0` for that case so the coverage is kept.

## Accessibility text background

Independent of which font path is active, `gui_textBackground` draws a solid
black backing behind each line of text so contrast no longer depends on what
happens to be underneath.

| Cvar | Default | Meaning |
| --- | --- | --- |
| `gui_textBackground` | `0` | Backing opacity; 0 off, 1 opaque |
| `gui_textBackgroundPadding` | `2` | Padding past the text, in virtual units |

The box is drawn once per line before any glyph, so it never shows through the
gaps between characters, and colour escapes inside a line change the text colour
without affecting the backing.

Its height comes from the font's **measured glyph ink extents**, not from
`fontInfo_t`'s `ascender`/`descender`. Those fields do not describe where the ink
is: the retail marine font declares an ascender of 29.9 while its capitals reach
40.4, and declares no descender at all despite having glyphs 11 units below the
baseline. Measuring the glyphs also means every line of a given font gets the
same box height whatever characters it contains, so a wrapped paragraph does not
come out ragged. `uiFontParitySelfTest` covers both the extent measurement and
the rect placement.

## Known limitations

- **Only codepoints 32–255 are reachable from the text path.** The font files
  carry the full extended coverage, and `r_ttfFontDebug` will show it, but
  `idDeviceContext` still indexes glyphs by byte, so Greek, Cyrillic, Arabic and
  Hebrew cannot be displayed yet. Reaching them needs UTF-8 decoding and a
  codepoint-keyed glyph query in the text path.
- **No Arabic shaping or bidi.** The faces include the Presentation Forms-B
  joined shapes precisely so a shaper can use them, but no shaper exists yet.
  Until one does, Arabic coverage is not usable text.
- Atlases are rebuilt only when fonts are registered; a resolution change does
  not currently re-rasterise them at the new upscale factor, so changing
  resolution wants a restart for text to be pixel-exact again.
- `FMT_ALPHA` would quarter atlas memory and is swizzled to RGB=1/A=R on both
  backends, but a `ScratchImage` in that format renders nothing through the GUI
  blend path. Unresolved; RGBA8 is used instead.
