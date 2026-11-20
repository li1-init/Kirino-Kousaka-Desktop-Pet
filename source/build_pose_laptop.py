"""Build eyes-only idle and moving, bubble-free thinking for the native pet."""

import io
import json
import subprocess
from bisect import bisect_right
from itertools import accumulate
from zipfile import ZIP_DEFLATED, ZipFile

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw

from build_calm import EYES, save_animation, softened_patch
from build_upgrade import PROJECT, ROWS, cell_box, clear_transparent_rgb, fit_frames, landmarks, render


SRC = PROJECT / "source" / "pose"
OUTPUT = PROJECT / "build" / "pose-and-laptop"
BASE = "calm-idle-2026-11-20"
HOLDS = (700, 420, 1200, 720, 520, 1040)
TRAVEL = (420, 420, 360, 480, 480, 440)
BLINK_TIMES = (0, 4770, 4830, 4940, 5010)
BLINK_PHASES = (0, 1, 2, 3, 0)


def from_git(name):
    return subprocess.check_output(["git", "-C", str(PROJECT), "show", f"{BASE}:pet/{name}"])


def sources(state):
    paths = sorted((SRC / "frames" / state).glob("*.png"))
    assert len(paths) == 6, (state, len(paths))
    return [Image.open(path).convert("RGBA") for path in paths]


def optical_inbetweens(first, second, count):
    dimensions = (first.height, first.width)
    y, x = np.indices(dimensions, dtype=np.float32)
    grid = np.dstack((x, y))

    def premultiply(image):
        pixels = np.array(image, dtype=np.float32) / 255
        pixels[..., :3] *= pixels[..., 3:4]
        grayscale = cv2.cvtColor(pixels[..., :3], cv2.COLOR_RGB2GRAY)
        return pixels, np.uint8(np.clip(255 * grayscale, 0, 255))

    a, gray_a = premultiply(first)
    b, gray_b = premultiply(second)
    forward = cv2.calcOpticalFlowFarneback(gray_a, gray_b, None, .5, 3, 15, 3, 5, 1.2, 0)
    backward = cv2.calcOpticalFlowFarneback(gray_b, gray_a, None, .5, 3, 15, 3, 5, 1.2, 0)
    for step in range(1, count + 1):
        t = step / (count + 1)
        before = cv2.remap(a, grid - forward * t, None, cv2.INTER_LINEAR)
        after = cv2.remap(b, grid - backward * (1 - t), None, cv2.INTER_LINEAR)
        mix = before * (1 - t) + after * t
        alpha = mix[..., 3:4]
        mix[..., :3] = np.divide(mix[..., :3], alpha, out=np.zeros_like(mix[..., :3]), where=alpha > 0)
        frame = Image.fromarray(np.uint8(np.clip(np.rint(mix * 255), 0, 255)))
        clear_transparent_rgb(frame)
        yield frame


def thinking_motion(poses):
    frames, durations = [], []
    for index, (pose, hold, travel) in enumerate(zip(poses, HOLDS, TRAVEL, strict=True)):
        frames.append(pose)
        durations.append(hold)
        next_pose = poses[(index + 1) % len(poses)]
        inbetweens = list(optical_inbetweens(pose, next_pose, 4))
        interval = travel // len(inbetweens)
        frames.extend(inbetweens)
        durations.extend([interval] * len(inbetweens))
    return frames, durations


def idle_phases(prior):
    base = prior.crop(cell_box(0, 0)).convert("RGBA")
    frames = [base]
    looks = [[prior.crop(cell_box(row, col)).convert("RGBA") for row in (9, 10) for col in range(8)]]
    mask = Image.new("1", base.size)
    marker = ImageDraw.Draw(mask)
    for left, top, right, bottom in EYES:
        marker.rectangle((left, top, right - 1, bottom - 1), fill=1)

    for phase in (2, 3, 4):
        prior.seek(phase)
        previous = prior.crop(cell_box(0, 0)).convert("RGBA")
        frame = base.copy()
        for box in EYES:
            softened_patch(frame, previous, box)
        diff = ImageChops.difference(base, frame)
        diff.paste((0, 0, 0, 0), mask=mask)
        assert not diff.getbbox(alpha_only=False), "Idle pixels outside the eyes moved."
        frames.append(frame)
        looks.append([prior.crop(cell_box(row, col)).convert("RGBA")
                      for row in (9, 10) for col in range(8)])
    assert all(frame.tobytes() != base.tobytes() for frame in frames[1:])
    return frames, looks


def tile(atlas, row, cells):
    for col, frame in enumerate(cells):
        atlas.paste(frame, cell_box(row, col)[:2])


def composed(base, idle, gaze, thinking):
    atlas = base.copy()
    tile(atlas, 0, [idle] * 6)
    tile(atlas, 7, [thinking] * 6)
    tile(atlas, 9, gaze[:8])
    tile(atlas, 10, gaze[8:])
    clear_transparent_rgb(atlas)
    return atlas


def timed_atlas(base, idle, gaze, poses, motion_durations):
    motion_times = [0, *accumulate(motion_durations)]
    offsets = sorted(set(motion_times).union(BLINK_TIMES))
    durations = [second - first for first, second in zip(offsets, offsets[1:])]

    def frames():
        for offset in offsets[:-1]:
            blink = BLINK_PHASES[bisect_right(BLINK_TIMES, offset) - 1]
            pose = poses[bisect_right(motion_times, offset) - 1]
            yield composed(base, idle[blink], gaze[blink], pose)

    return frames, durations


def seated_frames():
    extracted = sources("laptop")
    max_height = max(image.getchannel("A").getbbox()[3] - image.getchannel("A").getbbox()[1]
                     for image in extracted)
    scale = 143 / max_height
    sprites = []
    for original in extracted:
        frame = original.resize((round(original.width * scale), round(original.height * scale)),
                                Image.Resampling.LANCZOS)
        left, _, right, bottom = frame.getchannel("A").getbbox()
        sprite = Image.new("RGBA", (192, 208))
        sprite.paste(frame, (round(97 - (left + right) / 2), 192 - bottom))
        sprites.append(sprite)
    return sprites


def output_preview(path, frames, durations):
    shots = [render(frame, scale=2) for frame in frames]
    shots[0].save(path, save_all=True, append_images=shots[1:], duration=list(durations),
                  loop=0, disposal=2)


def main():
    prior = Image.open(io.BytesIO(from_git("spritesheet.webp")))
    base = prior.convert("RGBA")
    idle, gaze = idle_phases(prior)
    poses = fit_frames(sources("running"), idle[0])
    _, baseline, midpoint = landmarks(idle[0])
    for pose in poses:
        _, shoe_y, shoe_x = landmarks(pose)
        assert abs(shoe_y - baseline) <= 1 and abs(shoe_x - midpoint) <= 1
    moving, motion_durations = thinking_motion(poses)
    frames, times = timed_atlas(base, idle, gaze, moving, motion_durations)

    package = OUTPUT / "kirino-chibi"
    package.mkdir(parents=True, exist_ok=True)
    sprite = package / "spritesheet.webp"
    save_animation(sprite, frames(), times)
    assert sprite.stat().st_size <= 20 * 1024 * 1024
    with Image.open(sprite) as encoded:
        assert encoded.n_frames == len(times)
        for index, (duration, expected) in enumerate(zip(times, frames(), strict=True)):
            encoded.seek(index)
            actual = encoded.convert("RGBA")
            assert encoded.info["duration"] == duration
            assert actual.tobytes() == expected.tobytes(), index
            if index == 0:
                for row, (_, count) in enumerate(ROWS):
                    for col in range(8):
                        assert bool(actual.crop(cell_box(row, col)).getchannel("A").getbbox()) == (col < count)

    manifest = json.loads(from_git("pet.json"))
    manifest["description"] = "桐乃 Q 版宠物。站立待机时轻轻眨眼，任务运行时会托腮侧倾思考。"
    (package / "pet.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with ZipFile(OUTPUT / "kirino-codex-pet.zip", "w", ZIP_DEFLATED) as archive:
        for asset in sorted(package.iterdir()):
            archive.write(asset, f"{package.name}/{asset.name}")

    sync = base.copy()
    tile(sync, 0, [idle[index] for index in (0, 0, 2, 0, 0, 0)])
    tile(sync, 7, poses)
    clear_transparent_rgb(sync)
    sync.save(OUTPUT / "account-sheet.webp", lossless=True, method=6, exact=True)

    period = sum(times)
    blink_offsets = (*BLINK_TIMES, period)
    output_preview(OUTPUT / "eyes-only-idle.gif", [idle[phase] for phase in BLINK_PHASES],
                   [right - left for left, right in zip(blink_offsets, blink_offsets[1:])])
    output_preview(OUTPUT / "thinking-body-motion.gif", moving, motion_durations)
    laptop = seated_frames()
    strip = Image.new("RGBA", (6 * 192, 208))
    tile(strip, 0, laptop)
    clear_transparent_rgb(strip)
    strip.save(OUTPUT / "laptop-strip.webp", lossless=True, method=6, exact=True)
    output_preview(OUTPUT / "laptop-idle.gif", laptop, (530, 330, 440, 720, 420, 690))
    montage = Image.new("RGB", (6 * 192, 3 * 208), "#222831")
    for row, sprites in enumerate((poses, [idle[0], *idle, idle[0]], laptop)):
        for column, art in enumerate(sprites):
            montage.paste(render(art), (column * 192, row * 208))
    montage.save(OUTPUT / "pose-and-laptop-frames.png")
    print(f"{len(times)} frames, {period} ms, {sprite.stat().st_size} bytes")


if __name__ == "__main__":
    main()
