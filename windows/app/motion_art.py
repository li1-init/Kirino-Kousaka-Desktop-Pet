"""Animate the Windows artwork on a continuous, transparent 192×208 canvas."""

import math

from PIL import Image


CELL = (192, 208)
COLUMNS = 8
GROUND = 195


def atlas_cell(atlas, row, column):
    x, y = column * CELL[0], row * CELL[1]
    return atlas.crop((x, y, x + CELL[0], y + CELL[1]))


def warp(sprite, offset):
    # Deform the complete sprite with a single mesh. Adjacent body regions
    # share their control points, including across the hips and shoulders.
    width, height = CELL
    points = {
        (x, y): (x - dx, y - dy)
        for y in range(0, height + 1, 8)
        for x in range(0, width + 1, 8)
        for dx, dy in [offset(x, y)]
    }
    mesh = []
    for top in range(0, height, 8):
        for left in range(0, width, 8):
            right, bottom = left + 8, top + 8
            corners = ((left, top), (left, bottom), (right, bottom), (right, top))
            mesh.append(((left, top, right, bottom), tuple(value for corner in corners for value in points[corner])))
    return sprite.convert("RGBa").transform(CELL, Image.Transform.MESH, mesh, Image.Resampling.BICUBIC).convert("RGBA")


def smoothstep(value):
    value = min(1, max(0, value))
    return value * value * (3 - 2 * value)


def pose(sprite, shift=0, crouch=0, lift=0, scale=1, head=0, step=0):
    def offset(x, y):
        torso = 1 - smoothstep((y - 118) / 68)
        head_weight = 1 - smoothstep((y - 56) / 42)
        leg_weight = smoothstep((y - 122) / 42)
        lean = shift * torso + head * head_weight
        feet = step * leg_weight * (1 if x > 96 else -1)
        return ((x - 96) * (scale - 1) + lean + feet,
                (y - GROUND) * (scale - 1) + crouch * torso - lift)

    return warp(sprite, offset)


def standing_motion(frames, keys):
    """Interpolate body movement independently of the authored pose changes."""
    for before, after in zip(keys, keys[1:]):
        duration, art, *origin = before
        destination = after[2:]
        count = math.ceil(duration / 64)
        for index in range(count):
            blend = smoothstep(index / count)
            values = [a + (b - a) * blend for a, b in zip(origin, destination)]
            yield pose(frames[art], *values), ((index + 1) * duration // count - index * duration // count)
    duration, art, *values = keys[-1]
    yield pose(frames[art], *values), duration


def typing_motion(frames):
    # Two uneven bursts, a short reading pause, then a final quick pair.
    # The arms and head shift while the laptop and table stay in place.
    taps = ((180, 446, 744, 1260, 1540, 2470, 2730, 3325),
            (318, 590, 900, 1390, 1710, 2610, 3010, 3470))

    def effort(times, t):
        return max((math.cos(math.pi * (t - tap) / 190) ** 2
                    for tap in times if abs(t - tap) <= 95), default=0)

    for elapsed in range(0, 4000, 50):
        left, right = (effort(hand, elapsed) for hand in taps)
        busy = left + right
        rest = math.exp(-((elapsed - 2150) / 330) ** 2)
        breathing = math.sin(math.tau * elapsed / 4000)

        def offset(x, y):
            left_hand = math.exp(-((x - 92) / 9) ** 2 - ((y - 143) / 8) ** 2)
            right_hand = math.exp(-((x - 111) / 15) ** 2 - ((y - 145) / 9) ** 2)
            upper = smoothstep((x - 74) / 22) * (1 - smoothstep((y - 104) / 35))
            above_desk = 1 - smoothstep((y - 148) / 9)
            dx = -1.8 * left * left_hand + 2.4 * right * right_hand - (busy * 0.9 + rest * 1.5) * upper
            dy = -3.8 * left * left_hand - 3.4 * right * right_hand + (busy * 1.2 + rest * 2 + breathing * 0.7) * upper
            return dx * above_desk, dy * above_desk

        frame = (1 if left > right else 4) if busy > 0.4 else 0
        yield warp(frames[frame], offset), 50


def write_motion(output, name, sequence):
    frames = list(sequence)
    rows = math.ceil(len(frames) / COLUMNS)
    with Image.new("RGBA", (CELL[0] * COLUMNS, CELL[1] * rows)) as atlas:
        for index, (frame, _) in enumerate(frames):
            atlas.paste(frame, (index % COLUMNS * CELL[0], index // COLUMNS * CELL[1]))
        atlas.save(output / f"{name}.png")
    return [duration for _, duration in frames]


def standing_sequences(atlas, jump):
    idle = atlas_cell(atlas, 0, 0)
    return {
        # Keyframes contain duration, artwork, weight shift, knee bend,
        # lift, scale, head follow-through and stance width.
        "waiting": standing_motion([atlas_cell(atlas, 6, n) for n in range(6)], [
            (460, 0, 0, 0, 0, 1, 0, 0), (430, 1, -3, 3, 0, 1, -1, 1),
            (560, 2, -6, 5, 0, 1, 0, 2), (740, 3, -4, 4, 0, 1, 2, 2),
            (610, 4, 3, 3, 0, 1, -2, 1), (450, 5, 2, 2, 0, 1, 0, 0),
            (360, 0, 0, 0, 0, 1, 0, 0),
        ]),
        "review": standing_motion([atlas_cell(atlas, 8, n) for n in range(6)], [
            (440, 0, 0, 0, 0, 1, 0, 0), (450, 1, -3, 3, 0, 1, -1, 1),
            (500, 2, -4, 5, 0, 1, 0, 2), (650, 3, 0, 2, 0, 1, 1, 2),
            (850, 4, 5, 1, 0, 1, 2, 2), (470, 5, 2, 3, 0, 1, -1, 1),
            (330, 0, 0, 0, 0, 1, 0, 0),
        ]),
        "hug": standing_motion([idle, *[atlas_cell(atlas, 4, n) for n in range(5)]], [
            (390, 0, 0, 0, 0, 1, 0, 0), (440, 1, -3, 3, 0, 1, -2, 1),
            (460, 2, -4, 5, 0, 1, 0, 1), (510, 3, 1, 4, 0, 1, 2, 2),
            (820, 4, 5, 5, 0, 1, 1, 1), (630, 5, 2, 3, 0, 1, 0, 0),
            (340, 0, 0, 0, 0, 1, 0, 0),
        ]),
        "jumping": standing_motion([idle, atlas_cell(jump, 0, 0)], [
            (260, 0, 0, 0, 0, 1, 0, 0), (300, 0, -2, 8, 0, 0.97, 0, 1),
            (240, 1, 0, 5, 0, 0.93, 0, 1), (250, 1, 2, 0, 22, 0.88, 1, -2),
            (240, 1, 1, 1, 17, 0.9, 0, -1), (250, 1, 0, 8, 0, 0.96, -1, 2),
            (300, 1, 0, 3, 0, 0.99, 0, 0), (260, 0, 0, 0, 0, 1, 0, 0),
        ]),
        "failed": standing_motion([idle, *[atlas_cell(atlas, 5, n) for n in range(8)]], [
            (360, 0, 0, 0, 0, 1, 0, 0), (340, 1, -2, 2, 0, 1, 0, 1),
            (410, 3, -4, 4, 0, 1, -1, 2), (460, 4, -2, 6, 0, 1, 1, 2),
            (590, 5, 1, 8, 0, 1, -3, 2), (390, 6, 0, 6, 0, 1, 3, 1),
            (360, 7, -1, 3, 0, 1, -1, 0), (310, 0, 0, 0, 0, 1, 0, 0),
        ]),
    }
