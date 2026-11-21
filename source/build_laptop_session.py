"""Render the silent seated reaction from its six drawn poses."""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from build_laptop_work import assert_patch, encode_motion, normalize, read_frames, remove_shoes
from build_pose_laptop import optical_inbetweens, output_preview
from build_upgrade import PROJECT, clear_transparent_rgb, render


SOURCE = PROJECT / "source" / "laptop-session"
OUTPUT = PROJECT / "build" / "laptop-session"
HOLDS = (300, 450, 600, 180, 450, 620)
TRAVEL = (440, 480, 300, 420, 760)
MOTION_FPS = 60
GIF_FPS = 50
# The edge follows the laptop lid and stays above the fingers and the desk.
UPPER_BODY = (
    (0, 0), (191, 0), (191, 145), (146, 146), (131, 140),
    (121, 133), (118, 124), (84, 123), (78, 99), (0, 95),
)
# Boundaries in the final 192 x 208 cell, after the pose has been fitted.
STATIONARY_FOREGROUND = (
    ((38, 116), (69, 116), (79, 118), (86, 125), (90, 143), (94, 154), (37, 158)),
    ((84, 139), (100, 140), (109, 142), (117, 143), (122, 149), (120, 152), (87, 152)),
)
STATIONARY_LOWER_Y = 153
# Small offsets of the shoulders in the fitted cell. The pelvis is pinned.
TORSO_OFFSETS = ((0, 0), (-0.7, 0.2), (-1.5, 0.4), (-2.0, 0.2), (-0.4, 0.5), (0, 0))
CHEEK_CENTERS = (
    ((94, 105), (115, 104)), ((92, 105), (115, 103)),
    ((92, 103), (116, 101)), ((91, 101), (114, 97)),
    ((89, 108), (112, 104)), ((94, 105), (115, 104)),
)
BLUSH_STRENGTHS = (0, 0.25, 1, 0.95, 0.10, 0)


def smoothstep(value):
    value = np.clip(value, 0, 1)
    return value * value * (3 - 2 * value)


def add_reaction_detail(frame, index, phase, grid, torso_weight):
    next_index = min(index + 1, len(TORSO_OFFSETS) - 1)
    # The face starts turning before the shoulders follow, and settles first.
    torso_phase = float(smoothstep((phase - 0.18) / 0.82))
    torso_start = np.array(TORSO_OFFSETS[index], dtype=np.float32)
    torso_end = np.array(TORSO_OFFSETS[next_index], dtype=np.float32)
    offset = torso_start + (torso_end - torso_start) * torso_phase
    face_phase = smoothstep(phase)
    strength = BLUSH_STRENGTHS[index] + (BLUSH_STRENGTHS[next_index] - BLUSH_STRENGTHS[index]) * face_phase
    if not offset.any() and not strength:
        return frame

    pixels = np.asarray(frame, dtype=np.float32) / 255
    if offset.any():
        pixels[..., :3] *= pixels[..., 3:4]
        sample = grid - torso_weight[..., None] * offset
        pixels = cv2.remap(pixels, sample, None, cv2.INTER_LINEAR)
        alpha = pixels[..., 3:4]
        pixels[..., :3] = np.divide(
            pixels[..., :3], alpha, out=np.zeros_like(pixels[..., :3]), where=alpha > 0
        )
    if strength:
        # Follow the cheeks as the head turns. Only warm, opaque skin receives tint.
        centers = np.array(CHEEK_CENTERS[index])
        centers = centers + (np.array(CHEEK_CENTERS[next_index]) - centers) * face_phase
        cheek_mask = np.zeros(grid.shape[:2], dtype=np.float32)
        for center in centers:
            distance = np.square((grid - center) / (6.2, 3.2)).sum(axis=-1)
            cheek_mask = np.maximum(cheek_mask, np.square(np.clip(1 - distance, 0, 1)))
        r, g, b, alpha = pixels.transpose(2, 0, 1)
        skin = smoothstep((r - 0.66) / 0.14) * smoothstep((g - b - 0.018) / 0.09)
        skin *= smoothstep((g - 0.44) / 0.20) * (alpha >= 0.98)
        amount = strength * cheek_mask * skin
        pixels[..., :3] += amount[..., None] * np.array((4, -12, -3), dtype=np.float32) / 255
    return Image.fromarray(np.uint8(np.rint(np.clip(pixels, 0, 1) * 255)))


def make_reaction(poses, mask, fps):
    rest = poses[0]
    outside = mask.point(lambda value: 0 if value else 255)
    poses_and_delays = []
    for index, (pose, duration) in enumerate(zip(poses, HOLDS, strict=True)):
        poses_and_delays.append((pose, duration, index, 0))
        if index < len(TRAVEL):
            travel = TRAVEL[index]
            count = round(travel * fps / 1000)
            boundaries = [round(step * travel / count) for step in range(count + 1)]
            for step, middle in enumerate(optical_inbetweens(pose, poses[index + 1], count, eased=True)):
                middle.paste(rest, mask=outside)
                phase = (step + 1) / (count + 1)
                poses_and_delays.append((middle, boundaries[step + 1] - boundaries[step], index, phase))
    normalize_pose = normalize(rest)
    fitted_rest = normalize_pose(rest)
    y, x = np.indices((fitted_rest.height, fitted_rest.width), dtype=np.float32)
    grid = np.dstack((x, y))
    torso_weight = smoothstep((y - 108) / 13) * smoothstep((151 - y) / 16)
    torso_weight *= smoothstep((x - 78) / 15) * smoothstep((158 - x) / 18)
    stationary_foreground = Image.new("L", fitted_rest.size)
    for outline in STATIONARY_FOREGROUND:
        ImageDraw.Draw(stationary_foreground).polygon(outline, fill=255)
    ImageDraw.Draw(stationary_foreground).rectangle(
        (0, STATIONARY_LOWER_Y, fitted_rest.width - 1, fitted_rest.height - 1), fill=255
    )
    foreground_edge = stationary_foreground.filter(ImageFilter.GaussianBlur(1))
    movable = stationary_foreground.point(lambda value: 255 - value)
    frames, delays = [], []
    for pose, duration, index, phase in poses_and_delays:
        clear_transparent_rgb(pose)
        assert_patch(rest, pose, mask, "A frame changed outside the upper body.")
        fitted = add_reaction_detail(normalize_pose(pose), index, phase, grid, torso_weight)
        fitted = Image.composite(fitted_rest, fitted, foreground_edge)
        fitted.paste(fitted_rest, mask=stationary_foreground)
        clear_transparent_rgb(fitted)
        assert_patch(fitted_rest, fitted, movable, "A frame moved the hands, laptop, table or legs.")
        frames.append(fitted)
        delays.append(duration)
    assert sum(delays) == 5000
    assert len({frame.crop((105, 117, 151, 133)).tobytes() for frame in frames}) > 20
    return frames, delays


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rest = remove_shoes(read_frames(PROJECT / "source/pose/frames/laptop"))[0]
    drawings = read_frames(SOURCE / "frames" / "idle")
    mask = Image.new("L", rest.size)
    ImageDraw.Draw(mask).polygon(UPPER_BODY, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(2))
    poses = [rest, *[Image.composite(frame, rest, mask) for frame in drawings[1:5]], rest]
    frames, delays = make_reaction(poses, mask, MOTION_FPS)
    preview, preview_delays = make_reaction(poses, mask, GIF_FPS)
    with Image.open(PROJECT / "runtime/laptop-typing.webp") as typing:
        typing_frames, typing_delays = [], []
        for index in range(typing.n_frames):
            typing.seek(index)
            typing_frames.append(typing.convert("RGBA"))
            typing_delays.append(typing.info["duration"])
    assert frames[0].tobytes() == frames[-1].tobytes() == typing_frames[0].tobytes()
    assert preview[0].tobytes() == preview[-1].tobytes() == typing_frames[0].tobytes()
    encode_motion(OUTPUT / "laptop-thinking.webp", frames, delays)
    output_preview(OUTPUT / "laptop-seated-thinking.gif", preview, preview_delays)
    output_preview(OUTPUT / "laptop-task-silent.gif", typing_frames + preview + typing_frames,
                   typing_delays + preview_delays + typing_delays)
    contact = Image.new("RGB", (1152, 208), "#222831")
    starts = [0, *[sum(HOLDS[:index] + TRAVEL[:index]) for index in range(1, len(HOLDS))]]
    elapsed = 0
    for frame, delay in zip(frames, delays, strict=True):
        if elapsed in starts:
            contact.paste(render(frame), (starts.index(elapsed) * 192, 0))
        elapsed += delay
    contact.save(OUTPUT / "coordinated-contact.png")
    print(f"{len(frames)} source frames, 5000 ms, matched typing-to-thinking rest pose.")


if __name__ == "__main__":
    main()
