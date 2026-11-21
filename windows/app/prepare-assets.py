"""Convert the Windows WebP sources to WPF PNG atlases and frame timings."""

import json
import sys
from pathlib import Path

from PIL import Image

from motion_art import CELL, atlas_cell, standing_sequences, typing_motion, write_motion

ASSETS = Path(__file__).resolve().parents[1] / "assets"


def authored_clip(source):
    with Image.open(source) as clip:
        if clip.size != CELL or clip.n_frames < 2:
            raise ValueError(f"Expected an animated {CELL} clip: {source}")
        for index in range(clip.n_frames):
            clip.seek(index)
            frame = clip.convert("RGBA")
            duration = clip.info.get("duration", 0)
            if duration <= 0:
                raise ValueError(f"Missing frame duration: {source}, frame {index}")
            yield frame, duration


def main(output):
    output.mkdir(parents=True, exist_ok=True)
    with Image.open(ASSETS / "spritesheet.webp") as sheet, Image.open(ASSETS / "classic-jump.webp") as jump:
        if sheet.size != (1536, 2288):
            raise ValueError(f"Unexpected sprite sheet size: {sheet.size}")
        atlas = sheet.convert("RGBA")
        atlas.save(output / "spritesheet.png")
        sequences = standing_sequences(atlas, jump.convert("RGBA"))
        sequences["laptop-typing"] = typing_motion([atlas_cell(atlas, 7, n) for n in range(6)])
        sequences["laptop-thinking"] = authored_clip(ASSETS / "laptop-thinking.webp")
        timings = {name: write_motion(output, name, sequence) for name, sequence in sequences.items()}
    (output / "timings.json").write_text(json.dumps(timings) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
