"""Convert the Windows WebP sources to WPF PNG atlases and frame timings."""

import json
import sys
from pathlib import Path

from PIL import Image

from motion_art import CELL, atlas_cell, standing_sequences, typing_motion, write_motion

ASSETS = Path(__file__).resolve().parents[1] / "assets"
SESSION_ASSETS = ASSETS / "kirino-kyosuke-motion" / "action-motion" / "standard"
SESSION_CELL = (224, 232)
SESSION_CLIPS = {
    "cushion-typing": "22-kirino-cushion-typing.webp",
    "cushion-thinking": "23-kirino-cushion-thinking.webp",
    "cushion-glance": "24-kirino-cushion-glance.webp",
}
IDLE_CELL = (344, 232)
IDLE_CLIPS = {
    "phone-idle": "01-kirino-phone.webp",
}


def authored_clip(source, cell_size=CELL):
    with Image.open(source) as clip:
        if clip.size != cell_size or clip.n_frames < 2:
            raise ValueError(f"Expected an animated {cell_size} clip: {source}")
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
    for name, source in SESSION_CLIPS.items():
        timings[name] = write_motion(output, name, authored_clip(SESSION_ASSETS / source, SESSION_CELL), SESSION_CELL)
    for name, source in IDLE_CLIPS.items():
        timings[name] = write_motion(output, name, authored_clip(SESSION_ASSETS / source, IDLE_CELL), IDLE_CELL)
    (output / "timings.json").write_text(json.dumps(timings) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
