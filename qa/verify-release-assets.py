"""Verify the named poses and the contents of the Codex release ZIP."""

import io
import json
from pathlib import Path
from zipfile import ZipFile

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CELL_WIDTH = 192
CELL_HEIGHT = 208
ROW_COUNTS = (6, 8, 8, 4, 5, 8, 6, 6, 6, 8, 8)
NEW_ROWS = ((6, 6, "arms-crossed", 4), (8, 6, "show-game", 4), (4, 5, "hug-game", 3))


def cell(image, row, column):
    left = column * CELL_WIDTH
    top = row * CELL_HEIGHT
    return image.crop((left, top, left + CELL_WIDTH, top + CELL_HEIGHT)).convert("RGBA")


def verify_sheet(image, source):
    assert image.size == (1536, 2288), image.size
    for frame in range(image.n_frames):
        image.seek(frame)
        for row, count in enumerate(ROW_COUNTS):
            for column in range(count):
                assert cell(image, row, column).getchannel("A").getextrema() == (0, 255), (frame, row, column)
        for source_row, (row, count, name, example) in enumerate(NEW_ROWS):
            for column in range(count):
                assert cell(image, row, column).tobytes() == cell(source, source_row, column).tobytes()
            with Image.open(ROOT / "previews" / f"{name}.png") as picture:
                assert picture.convert("RGBA").tobytes() == cell(image, row, example).tobytes()


def clip_durations(path):
    with Image.open(path) as clip:
        assert clip.size == (CELL_WIDTH, CELL_HEIGHT), path
        durations = []
        for index in range(clip.n_frames):
            clip.seek(index)
            clip.load()
            assert clip.info["duration"] > 0, (path, index)
            durations.append(clip.info["duration"])
        return durations


def main():
    manifest = (ROOT / "pet" / "pet.json").read_bytes()
    sheet = (ROOT / "pet" / "spritesheet.webp").read_bytes()
    package = json.loads(manifest)
    assert package["id"] == "kirino-chibi"
    assert package["spritesheetPath"] == "spritesheet.webp"
    assert package["spriteVersionNumber"] == 2
    with ZipFile(ROOT / "releases" / "kirino-codex-pet.zip") as archive:
        assert sorted(archive.namelist()) == ["kirino-chibi/pet.json", "kirino-chibi/spritesheet.webp"]
        assert archive.read("kirino-chibi/pet.json") == manifest
        assert archive.read("kirino-chibi/spritesheet.webp") == sheet

    with (
        Image.open(ROOT / "source" / "hd" / "motion-cells.webp") as source,
        Image.open(io.BytesIO(sheet)) as native,
        Image.open(ROOT / "releases" / "kirino-account-sheet.webp") as account,
    ):
        assert native.n_frames > 1
        assert account.n_frames == 1
        verify_sheet(native, source)
        verify_sheet(account, source)

    assert len(clip_durations(ROOT / "runtime" / "laptop-typing.webp")) == 6
    assert sum(clip_durations(ROOT / "runtime" / "laptop-thinking.webp")) == 5000
    print("Codex package, transparency, motion slots, previews, and clip timings verified.")


if __name__ == "__main__":
    main()
