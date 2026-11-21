"""Verify Windows artwork, thumbnails, and the authored animation timing."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

from PIL import Image


WINDOWS = Path(__file__).resolve().parents[1]
ASSETS = WINDOWS / "assets"
CELL = (192, 208)
ROW_COUNTS = (6, 8, 8, 4, 5, 8, 6, 6, 6, 8, 8)
PREVIEWS = ((6, 4, "arms-crossed"), (8, 4, "show-game"), (4, 3, "hug-game"))


def cell(image, row, column):
    width, height = CELL
    return image.crop((column * width, row * height, (column + 1) * width, (row + 1) * height))


def clip_durations(name):
    with Image.open(ASSETS / name) as clip:
        assert clip.size == CELL, name
        durations = []
        for index in range(clip.n_frames):
            clip.seek(index)
            clip.load()
            durations.append(clip.info["duration"])
            assert durations[-1] > 0, (name, index)
        return durations


def verify_rendered_motions():
    with TemporaryDirectory() as temp:
        output = Path(temp)
        subprocess.run([sys.executable, str(WINDOWS / "app" / "prepare-assets.py"), str(output)], check=True)
        timings = json.loads((output / "timings.json").read_text(encoding="utf-8"))
        for name in ("waiting", "review", "hug", "failed", "jumping", "laptop-typing"):
            durations = timings[name]
            assert len(durations) >= 20 and all(duration > 0 for duration in durations), name
            assert sum(durations) >= 2000, (name, sum(durations))
            with Image.open(output / f"{name}.png") as atlas:
                frames = [cell(atlas, index // 8, index % 8) for index in range(len(durations))]
            bounds = [frame.getchannel("A").getbbox() for frame in frames]
            assert all(box and box[1] >= 2 and box[3] < CELL[1] for box in bounds), (name, bounds)
            if name in {"waiting", "review", "hug"}:
                leg_positions = {frame.crop((62, 135, 129, 195)).tobytes() for frame in frames}
                assert len(leg_positions) >= 12, name
            if name == "jumping":
                assert max(box[3] for box in bounds) - min(box[3] for box in bounds) >= 18
            if name == "laptop-typing":
                assert len({frame.crop((80, 131, 130, 151)).tobytes() for frame in frames}) >= 20
                assert len({frame.crop((25, 164, 158, 200)).tobytes() for frame in frames}) == 1


def main():
    project = ElementTree.parse(WINDOWS / "app" / "KirinoDesktopPet.csproj")
    assert project.find(".//ProjectReference") is None
    input_paths = project.find(".//PetAssetInput").get("Include").split(";")
    for name in input_paths:
        path = (WINDOWS / "app" / name.replace("\\", "/")).resolve(strict=True)
        assert path.is_relative_to(ASSETS), path

    with Image.open(ASSETS / "spritesheet.webp") as sheet:
        assert sheet.size == (1536, 2288) and sheet.n_frames == 1
        for row, count in enumerate(ROW_COUNTS):
            for column in range(count):
                assert cell(sheet, row, column).getchannel("A").getextrema() == (0, 255), (row, column)
        for row, column, name in PREVIEWS:
            with Image.open(WINDOWS / "previews" / f"{name}.png") as image:
                assert image.convert("RGBA").tobytes() == cell(sheet, row, column).tobytes(), name

    with Image.open(ASSETS / "classic-jump.webp") as jump:
        assert jump.size == (960, 208)
        assert all(cell(jump, 0, index).getchannel("A").getextrema() == (0, 255) for index in range(5))

    assert len(clip_durations("laptop-typing.webp")) == 6
    assert sum(clip_durations("laptop-thinking.webp")) == 5000
    verify_rendered_motions()
    print("Windows project inputs, artwork, previews and clip timings verified.")


if __name__ == "__main__":
    main()
