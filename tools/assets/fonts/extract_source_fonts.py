"""Pull the retail Quake 4 bitmap fonts out of an installed copy of the game.

The generator needs the ``fonts/english/*_48.fontdat`` metrics and their matching
``.tga`` atlases.  Those live inside the shipped pk4 archives, which are plain
zip files, so no game code is required to read them.

Usage:
    python extract_source_fonts.py --install "C:/.../Quake 4/q4base" --output .tmp/fontsrc
"""
from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

WANTED_SUFFIXES = (".fontdat", ".tga")


def extract(install: Path, output: Path, language: str) -> int:
	output.mkdir(parents=True, exist_ok=True)
	prefix = f"fonts/{language}/"
	found = 0

	# Later archives override earlier ones, which is the order the engine's
	# file system resolves them in, so sorting keeps the result faithful.
	for archive in sorted(install.glob("*.pk4")):
		try:
			bundle = zipfile.ZipFile(archive)
		except zipfile.BadZipFile:
			print(f"  skipping unreadable archive: {archive.name}")
			continue

		for entry in bundle.namelist():
			normalized = entry.replace("\\", "/").lower()
			if not normalized.startswith(prefix):
				continue
			if not normalized.endswith(WANTED_SUFFIXES):
				continue
			destination = output / Path(entry).name
			with bundle.open(entry) as source, open(destination, "wb") as target:
				shutil.copyfileobj(source, target)
			found += 1

	return found


def main() -> int:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--install", required=True, type=Path, help="path to the game's q4base directory")
	parser.add_argument("--output", required=True, type=Path)
	parser.add_argument("--language", default="english")
	arguments = parser.parse_args()

	if not arguments.install.is_dir():
		parser.error(f"not a directory: {arguments.install}")

	found = extract(arguments.install, arguments.output, arguments.language)
	if found == 0:
		print(f"No fonts/{arguments.language}/ entries found under {arguments.install}")
		return 1

	print(f"extracted {found} files to {arguments.output}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
