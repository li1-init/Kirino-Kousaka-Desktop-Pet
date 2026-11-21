"""Convert the shared WebP sources to WPF PNG atlases and frame timings."""

import json
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
CELL = (192, 208)
COLUMNS = 8


def prepare_clip(source, output, typing_frames=None):
    with Image.open(source) as clip:
        if clip.size != CELL or clip.n_frames < 2:
            raise ValueError(f"Expected an animated {CELL} clip: {source}")
        if typing_frames is not None and len(typing_frames) != clip.n_frames:
            raise ValueError(f"Typing artwork and timing counts differ: {source}")
        rows = (clip.n_frames + COLUMNS - 1) // COLUMNS
        durations = []
        with Image.new("RGBA", (CELL[0] * COLUMNS, CELL[1] * rows)) as atlas:
            for index in range(clip.n_frames):
                clip.seek(index)
                with clip.convert("RGBA") as original:
                    frame = original if typing_frames is None else typing_frames[index]
                    atlas.paste(frame, (index % COLUMNS * CELL[0], index // COLUMNS * CELL[1]))
                duration = clip.info.get("duration", 0)
                if duration <= 0:
                    raise ValueError(f"Missing frame duration: {source}, frame {index}")
                durations.append(duration)
            atlas.save(output)
    return durations


def main(output):
    output.mkdir(parents=True, exist_ok=True)
    with Image.open(ROOT / "pet" / "spritesheet.webp") as sheet:
        if sheet.size != (CELL[0] * COLUMNS, CELL[1] * 11):
            raise ValueError(f"Unexpected sprite sheet size: {sheet.size}")
        with sheet.convert("RGBA") as frame:
            frame.save(output / "spritesheet.png")
            typing_frames = [
                frame.crop((column * CELL[0], 7 * CELL[1], (column + 1) * CELL[0], 8 * CELL[1]))
                for column in range(6)
            ]
    with Image.open(ROOT / "source" / "hd" / "classic-jump.webp") as jump:
        jump.save(output / "classic-jump.png")

    timings = {
        name: prepare_clip(
            ROOT / "runtime" / f"{name}.webp", output / f"{name}.png",
            typing_frames if name == "laptop-typing" else None,
        )
        for name in ("laptop-typing", "laptop-thinking")
    }
    (output / "timings.json").write_text(json.dumps(timings) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
