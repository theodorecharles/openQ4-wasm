"""Reader for the retail Quake 4 ``.fontdat`` / atlas pair.

A ``.fontdat`` is a flat little-endian record: 256 glyphs of nine floats
(width, height, horiAdvance, horiBearingX, horiBearingY, s, t, s2, t2) followed
by four font-wide floats (pointSize, fontHeight, ascender, descender) and a
four byte serialised material pointer.  Every measurement is in pixels at the
file's point size, and the s/t pairs are normalised atlas coordinates.

The atlas itself is an RGBA TGA whose colour channels are a constant white; the
glyph coverage lives entirely in the alpha channel.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

GLYPHS_PER_FONT = 256
FONTDAT_SIZE = GLYPHS_PER_FONT * 9 * 4 + 4 * 4 + 4


@dataclass
class SourceGlyph:
	"""One glyph slot as recorded in a ``.fontdat``."""

	code: int
	width: float
	height: float
	advance: float
	bearing_x: float
	bearing_y: float
	s: float
	t: float
	s2: float
	t2: float

	@property
	def has_outline(self) -> bool:
		return self.width > 0.0 and self.height > 0.0 and self.s2 > self.s and self.t2 > self.t


@dataclass
class SourceFont:
	"""A single point size of one retail bitmap font."""

	name: str
	point_size: float
	font_height: float
	ascender: float
	descender: float
	glyphs: list[SourceGlyph]
	alpha: np.ndarray  # (h, w) uint8 coverage

	@property
	def atlas_width(self) -> int:
		return int(self.alpha.shape[1])

	@property
	def atlas_height(self) -> int:
		return int(self.alpha.shape[0])

	def coverage(self, glyph: SourceGlyph) -> np.ndarray:
		"""Return the glyph's coverage mask as float32 in ``[0, 1]``.

		The atlas rectangle is snapped to whole texels the same way the engine
		does when it samples the atlas, so the returned block matches what the
		bitmap renderer actually puts on screen.
		"""
		x0 = int(round(glyph.s * self.atlas_width))
		x1 = int(round(glyph.s2 * self.atlas_width))
		y0 = int(round(glyph.t * self.atlas_height))
		y1 = int(round(glyph.t2 * self.atlas_height))
		x0 = max(0, min(self.atlas_width, x0))
		x1 = max(0, min(self.atlas_width, x1))
		y0 = max(0, min(self.atlas_height, y0))
		y1 = max(0, min(self.atlas_height, y1))
		if x1 <= x0 or y1 <= y0:
			return np.zeros((0, 0), dtype=np.float32)
		return self.alpha[y0:y1, x0:x1].astype(np.float32) / 255.0


def read_fontdat(path: Path) -> tuple[list[SourceGlyph], dict[str, float]]:
	raw = path.read_bytes()
	if len(raw) != FONTDAT_SIZE:
		raise ValueError(f"{path}: expected {FONTDAT_SIZE} bytes, found {len(raw)}")

	metrics = struct.unpack("<%df" % (GLYPHS_PER_FONT * 9), raw[: GLYPHS_PER_FONT * 9 * 4])
	glyphs = []
	for index in range(GLYPHS_PER_FONT):
		block = metrics[index * 9 : index * 9 + 9]
		glyphs.append(SourceGlyph(index, *block))

	tail = GLYPHS_PER_FONT * 9 * 4
	point_size, font_height, ascender, descender = struct.unpack("<4f", raw[tail : tail + 16])
	return glyphs, {
		"point_size": point_size,
		"font_height": font_height,
		"ascender": ascender,
		"descender": descender,
	}


def load_source_font(directory: Path, name: str, size: int) -> SourceFont:
	glyphs, header = read_fontdat(directory / f"{name}_{size}.fontdat")
	image = Image.open(directory / f"{name}_{size}.tga")
	if image.mode != "RGBA":
		image = image.convert("RGBA")
	alpha = np.asarray(image)[:, :, 3].copy()
	return SourceFont(
		name=name,
		point_size=header["point_size"],
		font_height=header["font_height"],
		ascender=header["ascender"],
		descender=header["descender"],
		glyphs=glyphs,
		alpha=alpha,
	)
