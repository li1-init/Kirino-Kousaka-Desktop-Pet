"""Build the socked laptop typing row and the head-only seated pause."""

import io
import json
import subprocess
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from build_calm import save_animation
from build_pose_laptop import optical_inbetweens, output_preview, tile
from build_upgrade import PROJECT, ROWS, cell_box, clear_transparent_rgb, render


BASE = "thinking-posture-2026-11-20"
SOURCE = PROJECT / "source" / "laptop-work"
OUTPUT = PROJECT / "build" / "laptop-work"
FOOT = (127, 157, 174, 200)
SHOE_OUTLINE = (
    (12, 13), (17, 9), (23, 9), (30, 14), (37, 22), (38, 31),
    (35, 37), (30, 38), (22, 33), (18, 29), (15, 25), (14, 20),
)
TYPE_DURATIONS = (530, 330, 440, 720, 420, 690)
HEAD_HOLDS = (340, 420, 920, 450, 470, 400)


def baseline(path):
    return subprocess.check_output(["git", "-C", str(PROJECT), "show", f"{BASE}:{path}"])


def read_frames(folder):
    frames = [Image.open(path).convert("RGBA") for path in sorted(folder.glob("*.png"))]
    assert len(frames) == 6
    return frames


def assert_patch(original, edited, allowed, description):
    diff = ImageChops.difference(original, edited)
    diff.paste((0, 0, 0, 0), mask=allowed.point(lambda value: 255 if value else 0))
    assert not diff.getbbox(alpha_only=False), description


def remove_shoes(frames):
    width, height = FOOT[2] - FOOT[0], FOOT[3] - FOOT[1]
    sock = Image.open(SOURCE / "decoded" / "sock-detail.png").convert("RGBA")
    sock = sock.resize((width, height), Image.Resampling.LANCZOS)
    mask = Image.new("L", sock.size)
    ImageDraw.Draw(mask).polygon(SHOE_OUTLINE, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(0.7))
    allowed = Image.new("L", frames[0].size)
    allowed.paste(mask, FOOT[:2])
    changed = []
    for frame in frames:
        edited = frame.copy()
        edited.paste(sock, FOOT[:2], mask)
        clear_transparent_rgb(edited)
        clean = frame.copy()
        clear_transparent_rgb(clean)
        assert_patch(clean, edited, allowed, "Typing changed outside the shoe region.")
        assert edited.tobytes() != clean.tobytes()
        changed.append(edited)
    return changed


def head_mask(size):
    mask = Image.new("L", size)
    pixels = mask.load()
    for y in range(107):
        for x in range(size[0]):
            # Feather at the neckline and leave the left edge of the notebook alone.
            edge = 96 if x < 83 else 107
            pixels[x, y] = min(255, max(0, round((edge - y) * 255 / 17)))
    return mask


def thinking_frames(rest, references):
    mask = head_mask(rest.size)
    keyframes = [rest] + [Image.composite(frame, rest, mask) for frame in references[1:5]] + [rest]
    frames, timings = [], []
    for index, (frame, delay) in enumerate(zip(keyframes, HEAD_HOLDS, strict=True)):
        frames.append(frame)
        timings.append(delay)
        if index + 1 < len(keyframes):
            for middle in optical_inbetweens(frame, keyframes[index + 1], 4):
                # Keep all non-head pixels exactly equal to the restful keyboard pose.
                safe = middle.copy()
                safe.paste(rest, mask=mask.point(lambda value: 0 if value else 255))
                frames.append(safe)
                timings.append(100)
    assert sum(timings) == 5000
    for frame in frames:
        assert_patch(rest, frame, mask, "Thinking moved a keyboard, hand, or body pixel.")
    return frames, timings


def normalize(seated_ref):
    bounds = seated_ref.getchannel("A").getbbox()
    scale = 143 / (bounds[3] - bounds[1])
    size = (round(seated_ref.width * scale), round(seated_ref.height * scale))
    origin = (round(97 - (bounds[0] + bounds[2]) * size[0] / seated_ref.width / 2),
              192 - round(bounds[3] * size[1] / seated_ref.height))

    def to_cell(frame):
        target = Image.new("RGBA", (192, 208))
        target.paste(frame.resize(size, Image.Resampling.LANCZOS), origin)
        clear_transparent_rgb(target)
        return target

    return to_cell


def append_frame(frames, delays, frame, duration):
    if frames and not ImageChops.difference(frame, frames[-1]).getbbox(alpha_only=False):
        delays[-1] += duration
    else:
        frames.append(frame)
        delays.append(duration)


def encode_motion(path, frames, durations):
    unique, delays = [], []
    for frame, duration in zip(frames, durations, strict=True):
        append_frame(unique, delays, frame, duration)
    save_animation(path, unique, delays)
    with Image.open(path) as encoded:
        for index, (expected, ms) in enumerate(zip(unique, delays, strict=True)):
            encoded.seek(index)
            visible = encoded.convert("RGBA")
            assert visible.tobytes() == expected.tobytes()
            assert encoded.info["duration"] == ms


def package_native(typing):
    package = OUTPUT / "kirino-chibi"
    package.mkdir(parents=True, exist_ok=True)
    frames, durations = [], []
    with Image.open(io.BytesIO(baseline("pet/spritesheet.webp"))) as prior:
        for index in range(prior.n_frames):
            prior.seek(index)
            snapshot = prior.convert("RGBA")
            updated = snapshot.copy()
            tile(updated, 7, typing)
            for row, (_, count) in enumerate(ROWS):
                for col in range(8):
                    cell = cell_box(row, col)
                    cropped = updated.crop(cell)
                    assert bool(cropped.getchannel("A").getbbox()) == (col < count)
                    if row != 7:
                        assert cropped.tobytes() == snapshot.crop(cell).tobytes()
            append_frame(frames, durations, updated, prior.info["duration"])
    assert sum(durations) == 7200
    encode_motion(package / "spritesheet.webp", frames, durations)
    manifest = json.loads(baseline("pet/pet.json"))
    manifest["description"] = "桐乃 Q 版宠物。站立待机时轻轻眨眼，开始任务时坐着敲粉色笔记本。"
    (package / "pet.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with ZipFile(OUTPUT / "kirino-codex-pet.zip", "w", ZIP_DEFLATED) as archive:
        for asset in sorted(package.iterdir()):
            archive.write(asset, f"{package.name}/{asset.name}")

    sync = Image.open(io.BytesIO(baseline("releases/kirino-account-sheet.webp"))).convert("RGBA")
    tile(sync, 7, typing)
    sync.save(OUTPUT / "account-sheet.webp", lossless=True, method=6, exact=True)
    print("Native atlas:",len(frames),"frames;",sum(durations),"ms of unchanged ambient blink timing.")


def main():
    raw = read_frames(PROJECT / "source" / "pose" / "frames" / "laptop")
    typing = remove_shoes(raw)
    thinking, pauses = thinking_frames(typing[0], read_frames(SOURCE / "frames" / "idle"))
    fit = normalize(typing[0])
    tap_cells = [fit(frame) for frame in typing]
    head_cells = [fit(frame) for frame in thinking]
    package_native(tap_cells)

    strip = Image.new("RGBA", (6 * 192, 208))
    tile(strip, 0, tap_cells)
    strip.save(OUTPUT / "laptop-strip.webp", lossless=True, method=6, exact=True)
    encode_motion(OUTPUT / "laptop-typing.webp", tap_cells, TYPE_DURATIONS)
    encode_motion(OUTPUT / "laptop-thinking.webp", head_cells, pauses)
    output_preview(OUTPUT / "laptop-typing.gif", tap_cells, TYPE_DURATIONS)
    output_preview(OUTPUT / "laptop-seated-thinking.gif", head_cells, pauses)

    contact = Image.new("RGB", (6 * 192, 2 * 208), "#222831")
    for row, cells in enumerate((tap_cells, head_cells[::5])):
        for col, cell in enumerate(cells):
            contact.paste(render(cell), (col * 192, row * 208))
    contact.save(OUTPUT / "laptop-work-frames.png")
    detail = Image.new("RGB", (752, 344), "#222831")
    for index, frame in enumerate((raw[0], typing[0])):
        crop = frame.crop(FOOT).resize((376, 344), Image.Resampling.LANCZOS)
        detail.paste(crop, (index * 376, 0), crop)
    detail.save(OUTPUT / "review-sock-detail.png")
    print("Seated thinking length:", sum(pauses), "ms")


if __name__ == "__main__":
    main()
