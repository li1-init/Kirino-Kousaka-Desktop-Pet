"""Build the HD Codex package with the three new expressions."""

import io
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from build_calm import EYES, softened_patch
from build_laptop_work import assert_patch, baseline, encode_motion
from build_upgrade import PROJECT, cell_box, clear_transparent_rgb, render


SOURCE = PROJECT / "source" / "hd"
OUTPUT = PROJECT / "build" / "kirino-hd"
BASE = "ae3ab23ce73675ff8c04161e6e1f27abc25bfa07"
ACCOUNT_BASE = "2ea5cc6ca3de6d71240e1c7648e8d39e0e3d1f4e"
MOTION_ROWS = ((6, 6, "arms-crossed", 4), (8, 6, "show-game", 4), (4, 5, "hug-game", 3))


def fit_art(path: Path, reference):
    with Image.open(path) as source:
        art = source.convert("RGBA")
    # Very faint alpha around the generated edge can contain background specks.
    art.putalpha(art.getchannel("A").point(lambda value: value if value >= 24 else 0))
    left, top, right, bottom = reference.getbbox()
    fitted = ImageOps.contain(art.crop(art.getbbox()), (right - left, bottom - top), Image.Resampling.LANCZOS)
    result = Image.new("RGBA", reference.size)
    result.paste(fitted, (round((left + right - fitted.width) / 2), bottom - fitted.height))
    clear_transparent_rgb(result)
    return result


def blink_frame(standing, old_open, old_blink):
    if not ImageChops.difference(old_open, old_blink).getbbox(alpha_only=False):
        return standing
    frame = standing.copy()
    eye_mask = Image.new("L", frame.size)
    for bounds in EYES:
        softened_patch(frame, old_blink, bounds)
        ImageDraw.Draw(eye_mask).rectangle(
            (bounds[0], bounds[1], bounds[2] - 1, bounds[3] - 1), fill=255
        )
    assert_patch(standing, frame, eye_mask, "A blink changed pixels outside the eyes.")
    return frame


def typing_frames(atlas, typing):
    # Keep the authored key taps and fingers registered across all six frames.
    mask = Image.new("L", typing.size)
    ImageDraw.Draw(mask).polygon(
        ((83, 134), (105, 134), (114, 140), (113, 154), (86, 155), (80, 148)), fill=255
    )
    mask = mask.filter(ImageFilter.GaussianBlur(1.1))
    frames = [Image.composite(atlas.crop(cell_box(7, col)), typing, mask) for col in range(6)]
    for frame in frames:
        assert_patch(frames[0], frame, mask, "Typing moved outside the keyboard and fingers.")
    assert len({frame.tobytes() for frame in frames}) >= 5
    return frames


def update_atlas(original, idle, typing):
    atlas = original.copy()
    for row, frames in ((0, idle), (7, typing)):
        for col, frame in enumerate(frames):
            atlas.paste(frame, cell_box(row, col)[:2])
    clear_transparent_rgb(atlas)
    return atlas


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with Image.open(io.BytesIO(baseline("releases/kirino-account-sheet.webp", ACCOUNT_BASE))) as source:
        account = source.convert("RGBA")
    old_open = account.crop(cell_box(0, 0))
    standing = fit_art(SOURCE / "standing.png", old_open)
    typing = typing_frames(account, fit_art(SOURCE / "typing.png", account.crop(cell_box(7, 0))))

    atlases, delays = [], []
    with Image.open(io.BytesIO(baseline("pet/spritesheet.webp", BASE))) as native:
        for index in range(native.n_frames):
            native.seek(index)
            original = native.convert("RGBA")
            idle = [blink_frame(standing, old_open, original.crop(cell_box(0, col))) for col in range(6)]
            atlases.append(update_atlas(original, idle, typing))
            delays.append(native.info["duration"])

    # Account pets use the native row timeline and a single static sheet.
    closed = atlases[2].crop(cell_box(0, 0))
    account_atlas = update_atlas(account, [standing, standing, closed, standing, standing, standing], typing)
    with Image.open(SOURCE / "motion-cells.webp") as strip:
        for strip_row, (row, count, name, example) in enumerate(MOTION_ROWS):
            for column in range(count):
                pose = strip.crop(cell_box(strip_row, column))
                for atlas in [*atlases, account_atlas]:
                    atlas.paste(pose, cell_box(row, column)[:2])
                if column == example:
                    pose.save(OUTPUT / f"{name}.png")

    account_atlas.save(OUTPUT / "kirino-account-sheet.webp", lossless=True, exact=True, method=6)
    assert standing.tobytes() != closed.tobytes()

    package = OUTPUT / "kirino-chibi"
    package.mkdir(exist_ok=True)
    encode_motion(package / "spritesheet.webp", atlases, delays)
    (package / "pet.json").write_bytes(baseline("pet/pet.json", BASE))
    with ZipFile(OUTPUT / "kirino-codex-pet.zip", "w", ZIP_DEFLATED) as archive:
        for asset in sorted(package.iterdir()):
            archive.write(asset, f"{package.name}/{asset.name}")

    preview = Image.new("RGB", (192 * 6, 208 * 2), "#222831")
    for row, frames in enumerate(([old_open, standing, closed, standing], typing)):
        for col, frame in enumerate(frames):
            preview.paste(render(frame), (col * 192, row * 208))
    preview.save(OUTPUT / "kirino-hd-preview.png")


if __name__ == "__main__":
    main()
