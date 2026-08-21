"""Rebuild the openQ4 TrueType font set from the retail Quake 4 bitmap fonts.

Usage:
    python build_openq4_fonts.py --source <dir with *_48.fontdat/*.tga>
                                 --donors <dir with Noto*-var.ttf>
                                 --output <dir for the .ttf files>
                                 [--faces chain,marine,...]

The source directory is populated by ``extract_source_fonts.py``, which pulls
``fonts/english/*`` out of the installed Quake 4 pk4 archives.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from q4font.build import FaceBuilder, FaceSpec
from q4font.charset import unicode_ranges
from q4font.trace import TraceOptions

VERSION = "1.000"

FACES: dict[str, FaceSpec] = {
	"chain": FaceSpec(
		source="chain",
		family="openQ4 Chain",
		description="Wide squarish techno sans used across the Quake 4 menus and HUD.",
	),
	"lowpixel": FaceSpec(
		source="lowpixel",
		family="openQ4 LowPixel",
		description="Neo-grotesque companion face used for dense HUD readouts.",
	),
	"marine": FaceSpec(
		source="marine",
		family="openQ4 Marine",
		all_caps=True,
		description="All-caps military stencil face used for radio and objective text.",
	),
	"profont": FaceSpec(
		source="profont",
		family="openQ4 ProFont",
		description="Rounded technical face used for terminals and readouts.",
	),
	"r_strogg": FaceSpec(
		source="r_strogg",
		family="openQ4 Roman Strogg",
		all_caps=True,
		description="Angular oblique Strogg-Roman face used for Strogg interfaces.",
	),
	"bigchars": FaceSpec(
		source="bigchars",
		family="openQ4 BigChars",
		grid_atlas="bigchars.tga",
		description="Console and loading-screen face, traced from the fixed-cell bigchars sheet.",
	),
	"strogg": FaceSpec(
		source="strogg",
		family="openQ4 Strogg",
		extended=False,
		all_caps=True,
		description="Strogg rune face. Latin letters map to runes; other scripts are intentionally absent.",
	),
}


def composable_codepoints(second_pass: bool = False) -> list[int]:
	"""Everything worth attempting as base + mark, in a stable order."""
	ranges = unicode_ranges()
	blocks = ("greek", "cyrillic", "cyrillic_supp") if second_pass else ("latin_ext_a", "latin_ext_b", "latin_ext_add")
	wanted: list[int] = []
	for block in blocks:
		low, high = ranges[block]
		wanted.extend(range(low, high + 1))
	return wanted


def build_face(key: str, spec: FaceSpec, source: Path, donors: Path, output: Path) -> dict:
	started = time.perf_counter()
	builder = FaceBuilder(spec, source, donors, TraceOptions())

	builder.trace_source()
	metrics = builder.measure()
	builder.extract_marks(metrics)
	builder.compose(composable_codepoints())
	builder.alias_homoglyphs()
	# Accented Cyrillic whose base is a shared Latin shape (Yo, for instance)
	# is composed here so it uses the authentic letter rather than the donor's.
	# Anything whose base is donor-only is left for the donor, which keeps the
	# accent consistent with the letter underneath it.
	builder.compose(composable_codepoints(second_pass=True))
	builder.synthesize_shapes(metrics)
	builder.import_donors(metrics)
	builder.force_monospace()
	builder.fold_to_base()

	destination = output / f"{key}.ttf"
	builder.emit(destination, metrics, VERSION)

	elapsed = time.perf_counter() - started
	report = dict(builder.report)
	report.update(
		{
			"file": destination.name,
			"glyphs": len(builder.glyphs),
			"mapped": len(builder.cmap),
			"cap": metrics.cap_height,
			"xheight": metrics.x_height,
			"ascender": metrics.ascender,
			"descender": metrics.descender,
			"seconds": round(elapsed, 1),
			"bytes": destination.stat().st_size,
		}
	)
	return report


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--source", required=True, type=Path)
	parser.add_argument("--donors", required=True, type=Path)
	parser.add_argument("--output", required=True, type=Path)
	parser.add_argument("--faces", default="")
	arguments = parser.parse_args()

	keys = [k.strip() for k in arguments.faces.split(",") if k.strip()] or list(FACES)
	unknown = [k for k in keys if k not in FACES]
	if unknown:
		parser.error(f"unknown face(s): {', '.join(unknown)}")

	arguments.output.mkdir(parents=True, exist_ok=True)
	for key in keys:
		report = build_face(key, FACES[key], arguments.source, arguments.donors, arguments.output)
		summary = " ".join(f"{name}={value}" for name, value in report.items())
		print(f"{key:9s} {summary}", flush=True)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
