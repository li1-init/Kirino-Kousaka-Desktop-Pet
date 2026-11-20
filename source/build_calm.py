"""Build the calmer running pose and ambient idle motion for the native V2 atlas."""

import io
import json
import subprocess
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from build_upgrade import (
    PROJECT,
    ROWS,
    cell_box,
    clear_transparent_rgb,
    fit_frames,
    landmarks,
    render,
)


SOURCE = PROJECT / "source" / "calm"
OUTPUT = PROJECT / "build" / "calm-take"
BASE = "thinking-bubble-2026-11-20"
DURATIONS = (1800, 1100, 60, 110, 70, 2400)
EYES = ((78, 43, 95, 63), (97, 41, 116, 61))
LOOK_OFFSETS = (((-1, 3), (2, 2)), ((-2, 5), (0, 3)))


def read_base(file):
    return subprocess.check_output(["git", "-C", str(PROJECT), "show", f"{BASE}:pet/{file}"])


def fitted(state, neutral):
    files = sorted((SOURCE / "frames" / state).glob("*.png"))
    assert len(files) == 6, (state, len(files))
    return fit_frames([Image.open(path).convert("RGBA") for path in files], neutral)


def softened_patch(destination, source, region, dx=0, dy=0):
    item = source.crop(region)
    mask = Image.new("L", item.size)
    ImageDraw.Draw(mask).ellipse((1, 1, item.width - 2, item.height - 2), fill=255)
    destination.paste(item, (region[0] + dx, region[1] + dy), mask.filter(ImageFilter.GaussianBlur(1)))


def looking_frame(base, blink, row):
    frame = base.copy()
    for bounds, (dx, dy) in zip(EYES, LOOK_OFFSETS[row - 9]):
        softened_patch(frame, blink, bounds, dx, dy)
    return frame


def render_atlas(original, idle, thinking, blink):
    atlas = original.copy()
    for column in range(6):
        atlas.paste(idle, cell_box(0, column)[:2])
        atlas.paste(thinking, cell_box(7, column)[:2])
    if blink:
        for row in (9, 10):
            for column in range(8):
                box = cell_box(row, column)
                eyes = looking_frame(original.crop(box), idle, row)
                atlas.paste(eyes, box[:2])
    clear_transparent_rgb(atlas)
    return atlas


def little(value, length):
    return value.to_bytes(length, "little")


def riff_chunk(tag, data):
    return tag + little(len(data), 4) + data + bytes(len(data) % 2)


def save_animation(path, frames):
    # WebP frame rectangles must start at even coordinates. Lossless VP8L with
    # exact alpha preserves zero RGB in transparent pixels for the pet validator.
    width, height = frames[0].size
    extended_header = bytes((0x12, 0, 0, 0)) + little(width - 1, 3) + little(height - 1, 3)
    chunks = [b"WEBP", riff_chunk(b"VP8X", extended_header), riff_chunk(b"ANIM", bytes(6))]
    previous = None
    for frame, duration in zip(frames, DURATIONS):
        if previous is None:
            left, top, right, bottom = 0, 0, width, height
        else:
            rect = ImageChops.difference(frame, previous).getbbox(alpha_only=False)
            assert rect
            left, top, right, bottom = rect
        left -= left % 2
        top -= top % 2
        area = frame.crop((left, top, right, bottom))
        data = io.BytesIO()
        area.save(data, format="WEBP", lossless=True, exact=True, method=6)
        image_payload = data.getvalue()[12:]
        assert image_payload.startswith(b"VP8L")
        fields = (left // 2, top // 2, area.width - 1, area.height - 1, duration)
        # Flag 2 replaces pixels in the rectangle and retains the rest of the canvas.
        descriptor = b"".join(little(value, 3) for value in fields) + bytes((2,))
        chunks.append(riff_chunk(b"ANMF", descriptor + image_payload))
        previous = frame
    body = b"".join(chunks)
    path.write_bytes(b"RIFF" + little(len(body), 4) + body)


def preview(stills, row, column, path, durations=DURATIONS):
    shots = [render(atlas.crop(cell_box(row, column)), scale=2) for atlas in stills]
    shots[0].save(path, save_all=True, append_images=shots[1:], duration=list(durations),
                  loop=0, disposal=2)


def main():
    original = Image.open(io.BytesIO(read_base("spritesheet.webp"))).convert("RGBA")
    clear_transparent_rgb(original)
    reference = original.crop(cell_box(0, 0))
    idle = fitted("idle", reference)
    thinking = fitted("running", reference)
    resting = thinking[0]
    glance = resting.copy()
    settling = resting.copy()
    for bounds in EYES:
        softened_patch(glance, thinking[2], bounds)
        softened_patch(settling, thinking[4], bounds)
    assert len({frame.tobytes() for frame in (resting, glance, settling)}) == 3

    actions = (resting, glance, glance, glance, glance, settling)
    stills = [render_atlas(original, idle_frame, pose, blink=2 <= index <= 4)
              for index, (idle_frame, pose) in enumerate(zip(idle, actions))]
    package = OUTPUT / "kirino-chibi"
    package.mkdir(parents=True, exist_ok=True)
    sprites = package / "spritesheet.webp"
    save_animation(sprites, stills)

    with Image.open(sprites) as encoded:
        assert encoded.n_frames == len(stills)
        for index, (frame, duration) in enumerate(zip(stills, DURATIONS)):
            encoded.seek(index)
            restored = encoded.convert("RGBA")
            assert encoded.info["duration"] == duration
            assert restored.tobytes() == frame.tobytes(), ("WebP round trip", index)
            for row, (_, count) in enumerate(ROWS):
                for col in range(8):
                    box = cell_box(row, col)
                    cell = restored.crop(box)
                    assert bool(cell.getchannel("A").getbbox()) == (col < count)
                    if row not in (0, 7, 9, 10):
                        assert cell.tobytes() == original.crop(box).tobytes()

    manifest = json.loads(read_base("pet.json"))
    manifest["description"] = "桐乃 Q 版宠物。待机间歇眨眼、轻轻呼吸，任务运行时托腮思考。"
    (package / "pet.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")
    with ZipFile(OUTPUT / "kirino-codex-pet.zip", "w", ZIP_DEFLATED) as archive:
        for asset in package.iterdir():
            archive.write(asset, f"{package.name}/{asset.name}")

    preview(stills, 0, 0, OUTPUT / "idle-blink.gif")
    preview(stills, 9, 0, OUTPUT / "look-blink.gif")
    preview(stills, 7, 0, OUTPUT / "calm-thinking.gif")
    contact = Image.new("RGB", (6 * 192, 4 * 208), "#222831")
    for index, frame in enumerate(stills):
        for group, row in enumerate((0, 7, 9, 10)):
            contact.paste(render(frame.crop(cell_box(row, 0))), (index * 192, group * 208))
    contact.save(OUTPUT / "calm-motion-frames.png")
    print("Durations in milliseconds:", DURATIONS)
    print("Idle anchors:", [landmarks(frame) for frame in idle])
    print("Native package:", sprites)


if __name__ == "__main__":
    main()
