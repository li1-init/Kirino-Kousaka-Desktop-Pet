from pathlib import Path
from hashlib import sha256
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import local

import cv2
import numpy as np
from PIL import Image, ImageDraw

cv2.setNumThreads(1)
root = Path(__file__).resolve().parent.parent
output = root / "action-motion" / "standard"
FPS = 60
DURATION_MS = 3100
FRAME_COUNT = FPS * DURATION_MS // 1000
ATLAS_COLUMNS = 16
MIN_SPEED = 50
MAX_SPEED = 150
ATLAS_FRAMES = FRAME_COUNT * 100 // MIN_SPEED
CUSHION_TYPING_VERTICAL_SCALE = 0.5
motion_thread = local()


def estimate_flow(before, after):
    if not hasattr(motion_thread, "estimator"):
        estimator = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
        estimator.setFinestScale(0)
        estimator.setVariationalRefinementIterations(8)
        motion_thread.estimator = estimator
    return motion_thread.estimator.calc(before, after, None)


def timeline(source):
    poses, durations = [], []
    with Image.open(source) as gif:
        indices = [0, 3, 6, 9] if gif.n_frames == 36 and source.name.startswith("05-") else range(gif.n_frames)
        for i in indices:
            gif.seek(i)
            pose = gif.convert("RGBA")
            duration = gif.info["duration"]
            if len(indices) == 4 and source.name.startswith("05-"):
                # Movement along the desktop is driven by the window; the gait itself loops in place.
                offset = -70 + round(i * 140 / 35)
                registered = Image.new("RGBA", pose.size)
                registered.alpha_composite(pose, (-offset, 0))
                pose, duration = registered, 180
            if poses and pose.tobytes() == poses[-1].tobytes():
                durations[-1] += duration
            else:
                poses.append(pose)
                durations.append(duration)
    if poses[0].tobytes() == poses[-1].tobytes():
        durations[0] += durations.pop()
        poses.pop()
    return poses, durations


def prepare(poses, anchor_mask=None, bounds=None):
    boxes = [p.getchannel("A").getbbox() for p in poses]
    if bounds is None:
        bounds = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                  max(b[2] for b in boxes), max(b[3] for b in boxes))
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    target_width = 344 if width > height * 1.05 else 224
    target_height, ground = 232, 218
    scale = min((target_width - 30) / width, (ground - 16) / height)
    used = round(width * scale), round(height * scale)
    origin = (target_width - used[0]) // 2, ground - used[1]
    prepared = []
    for pose in poses:
        tile = pose.crop(bounds).resize(used, Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (target_width, target_height))
        canvas.alpha_composite(tile, origin)
        rgba = np.asarray(canvas, dtype=np.float32) / 255.0
        rgba[:, :, :3] *= rgba[:, :, 3:]
        prepared.append(rgba)
    x, y = np.meshgrid(np.arange(target_width, dtype=np.float32),
                       np.arange(target_height, dtype=np.float32))
    mask = None
    if anchor_mask is not None:
        mask_canvas = Image.new("L", (target_width, target_height))
        mask_canvas.paste(anchor_mask.crop(bounds).resize(used, Image.Resampling.NEAREST), origin)
        mask = np.asarray(mask_canvas, dtype=np.float32) / 255
    return prepared, np.stack((x, y), axis=-1), ground, mask


def remap(raster, sampling):
    return cv2.remap(raster, np.ascontiguousarray(sampling, dtype=np.float32), None, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)


def features(sprite):
    gray = cv2.cvtColor(sprite[:, :, :3], cv2.COLOR_RGB2GRAY)
    alpha = sprite[:, :, 3]
    # Transparent area acts as a stable background during motion estimation.
    return np.uint8(np.clip((gray + 0.48 * (1 - alpha)) * 255.0, 0, 255))


def head_anchor(sprite):
    ys, xs = np.where(sprite[:, :, 3] > 0.75)
    top = np.percentile(ys, 1)
    return np.array([np.median(xs[ys < top + 55]), top], dtype=np.float32)


def with_pose_prior(left, right, grid, change_x):
    head = head_anchor(left)
    delta = head_anchor(right) - head
    if not change_x:
        delta[0] = 0
    if np.linalg.norm(delta) < 10:
        return estimate_flow(features(left), features(right))
    y = grid[:, :, 1]
    influence = np.clip((253 - y) / max(55, 253 - head[1] - 68), 0, 1)
    prior = influence[:, :, None] * delta
    shifted = remap(left, sampling_for(grid, prior, 1))
    residual = estimate_flow(features(shifted), features(right))
    return prior + remap(residual, grid + prior)


def estimated_pair(left, right, grid, scene):
    fa, fb = features(left), features(right)
    if scene.startswith(("06-", "07-")):
        forward = with_pose_prior(left, right, grid, scene.startswith("07-"))
        backward = with_pose_prior(right, left, grid, scene.startswith("07-"))
    else:
        forward = estimate_flow(fa, fb)
        backward = estimate_flow(fb, fa)
    error_a = np.linalg.norm(forward + remap(backward, grid + forward), axis=2)
    error_b = np.linalg.norm(backward + remap(forward, grid + backward), axis=2)
    return forward, backward, error_a, error_b


def sampling_for(grid, vector, amount):
    sample = grid - amount * vector
    for _ in range(2):
        sample = 0.5 * (sample + grid - amount * remap(vector, sample))
    return sample


def inbetween(left, right, grid, pair, progress, single_pose=False):
    amount = progress * progress * (3 - 2 * progress)
    forward, backward, error_a, error_b = pair
    xa = sampling_for(grid, forward, amount)
    xb = sampling_for(grid, backward, 1 - amount)
    if single_pose:
        # Fast prop changes and crouches expose different silhouettes. Use one
        # moving outline per frame so a second hand or prop cannot show through.
        return remap(left, xa) if amount < .5 else remap(right, xb)
    a, b = remap(left, xa), remap(right, xb)
    wa = (1 - amount) / (1 + remap(error_a, xa) * 0.34)
    wb = amount / (1 + remap(error_b, xb) * 0.34)
    weight = wb / np.maximum(wa + wb, 0.0001)
    # Make disocclusions switch over shorter intervals than areas with matching artwork.
    mismatch = np.max(np.abs(a - b), axis=2)
    ambiguous = np.clip((mismatch - 0.04) * 9, 0, 1)
    # On newly exposed pixels, a single warped drawing keeps contours opaque.
    # Widen the short handoff only where the two warped drawings already agree.
    selection = np.clip((0.92 * amount + 0.08 * weight - 0.485) / 0.03, 0, 1)
    weight = weight * (1 - ambiguous) + selection * ambiguous
    return a * (1 - weight[:, :, None]) + b * weight[:, :, None]


# The left and right performers share a fixed stage. Each performer is registered
# against their own contact area where each foot position is part of the motion.
DUETS = {"05", "06", "08", "11", "12", "17"}
MOVING_FEET = {"04", "05", "06", "08", "15"}
CHAIR_SCENES = {"19", "20", "21"}
CUSHION_SCENES = {"22", "23", "24"}
SESSION_SCENES = CHAIR_SCENES | CUSHION_SCENES
DESK_SCENES = {"14", "18"} | SESSION_SCENES


def four_keyframes(source):
    with Image.open(source) as image:
        width, height = image.width // 2, image.height // 2
        poses = [
            image.crop((col * width, row * height, (col + 1) * width,
                        (row + 1) * height)).convert("RGBA")
            for row in range(2) for col in range(2)
        ]
    for pose in poses:
        # Remove low-alpha residue outside the drawings before estimating motion.
        pose.putalpha(pose.getchannel("A").point(lambda alpha: 0 if alpha < 19 else alpha))
    return poses


def session_poses(source):
    cushion = source.name[:2] in CUSHION_SCENES
    base_name = "22-kirino-cushion-typing.png" if cushion else "19-kirino-codex-typing.png"
    base = four_keyframes(source.with_name(base_name))
    reference = base[0]
    width, height = reference.size
    if source.name == base_name:
        poses = base
    else:
        variants = four_keyframes(source)
        poses = [reference, *(p.resize(reference.size, Image.Resampling.LANCZOS) for p in variants[1:])]

    def point(x, y):
        return round(x * width / 656), round(y * height / 599)

    # Source landmarks for the locked desk and laptop lid. Hands above the
    # keys stay outside the mask, so they can move without shifting the prop.
    lock = Image.new("L", (width, height))
    draw = ImageDraw.Draw(lock)
    if cushion:
        tabletop = 412
        laptop = ((94, 282), (239, 282), (247, 292), (273, 399),
                  (271, 412), (132, 413), (125, 404))
        left, right = 51, 584
    else:
        tabletop = 379
        laptop = ((105, 257), (245, 257), (253, 265), (271, 369),
                  (269, 379), (143, 380), (138, 375))
        left, right = 88, 565
    draw.rectangle((point(0, tabletop), (width - 1, height - 1)), fill=255)
    draw.polygon([point(x, y) for x, y in laptop], fill=255)
    # Keep the same registration when swapping Desk Pet actions.
    left, top = point(left, 0)
    right, bottom = point(right, 599)
    return poses, lock, (left, top, right, bottom)


def typing_sequence():
    # Brief rests between typing bursts use the open-eyed working pose.
    return [
        (0, 140), (1, 147), (2, 135), (1, 144), (2, 167), (0, 188),
        (2, 133), (1, 144), (2, 132), (1, 157), (0, 156),
        (2, 146), (1, 132), (0, 118), (2, 142),
        (0, 156), (1, 135), (2, 130), (1, 123), (2, 119), (0, 216),
    ]


def session_sequence(number):
    if number in {"20", "23"}:
        return [(0, 300), (1, 475), (2, 1280), (3, 580), (0, 465)]
    if number in {"21", "24"}:
        return [(0, 270), (1, 560), (2, 940), (3, 745), (0, 585)]
    return typing_sequence()


def alpha_points(pose):
    return np.where(np.asarray(pose.getchannel("A")) > 148)


def contact(pose, side, number):
    ys, xs = alpha_points(pose)
    if number == "01":
        keep = xs > pose.width * .5
    elif side == -1:
        keep = xs < pose.width / 2
    elif side == 1:
        keep = xs >= pose.width / 2
    else:
        keep = np.ones_like(xs, dtype=bool)
    ys, xs = ys[keep], xs[keep]
    floor = np.percentile(ys, 99)
    low = ys >= floor - (15 if number in DESK_SCENES else 12)
    return float(np.median(xs[low])), float(floor)


def registered_poses(poses, number):
    if number == "07":
        # Registration is based on the measured shoes and ignores the floor DVD.
        offsets = [(0, 0), (-1, 0), (0, -5), (9, -5), (0, -5)]
        assert len(poses) == len(offsets)
        result = []
        for pose, offset in zip(poses, offsets, strict=True):
            tile = Image.new("RGBA", pose.size)
            tile.alpha_composite(pose, offset)
            result.append(tile)
        return result

    sides = [-1, 1] if number in DUETS else [0]
    origin = [contact(poses[0], side, number) for side in sides]
    w, h = poses[0].size
    x, y = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    result = []
    for pose in poses:
        positions = [contact(pose, side, number) for side in sides]
        shifts = [(a[0] - b[0], a[1] - b[1]) for a, b in zip(origin, positions, strict=True)]
        # Keep the geometry of the acting stance in the walking and sitting poses.
        if number in {"05", "06", "08"}:
            shifts = [(0, dy) for _, dy in shifts]
        elif number in {"04", "15"}:
            shifts = [(float(np.clip(dx, -4, 4)), dy) for dx, dy in shifts]
        if len(sides) == 2:
            blend = np.clip((x - w * .37) / (w * .26), 0, 1)
            dx = shifts[0][0] * (1 - blend) + shifts[1][0] * blend
            dy = shifts[0][1] * (1 - blend) + shifts[1][1] * blend
        else:
            dx, dy = shifts[0]
        rgba = np.array(pose, dtype=np.float32) / 255
        rgba[:, :, :3] *= rgba[:, :, 3:]
        moved = remap(rgba, np.stack((x - dx, y - dy), axis=-1))
        result.append(unpremultiply(moved))
    return result


def lock_contacts(sprites, grid, ground, number):
    x, y = grid[:, :, 0], grid[:, :, 1]
    if number in MOVING_FEET or number == "01":
        return np.zeros_like(y), sprites[0]
    reference = sprites[2] if number == "07" else sprites[0]
    if number == "07":
        ys, xs = np.where((reference[:, :, 3] > .55) & (y >= ground - 28))
        area = (x >= xs.min() - 3) & (x <= xs.max() + 3)
        return area * np.clip((y - ys.min()) / 7, 0, 1), reference
    cutoff = ground - (24 if number in DESK_SCENES else 19)
    return np.clip((y - cutoff) / 6, 0, 1), reference


def unpremultiply(rgba):
    alpha = rgba[:, :, 3:]
    colors = np.divide(rgba[:, :, :3], alpha, out=np.zeros_like(rgba[:, :, :3]), where=alpha > 1/255)
    pixels = np.uint8(np.clip(np.concatenate((colors, alpha), axis=2) * 255 + .5, 0, 255))
    return Image.fromarray(pixels)


def pose_motion(sprite, grid, phase, number, lock, anchor):
    x, y = grid[:, :, 0], grid[:, :, 1]
    upper = np.clip((172 - y) / 108, 0, 1) ** 1.7
    if number in DESK_SCENES:
        upper *= np.clip((123 - y) / 70, 0, 1)
        if number == "18" or number in SESSION_SCENES:
            upper *= np.clip((x - x.shape[1] * .42) / 30, 0, 1)
    mid = x.shape[1] / 2
    if number in DUETS:
        mid = np.where(x < mid, x.shape[1] * .31, x.shape[1] * .69)
    theta = math.tau * phase
    # This is a local deformation around the upper body. The stage never pans.
    dx = (x - mid) * .014 * math.sin(theta) * upper
    dy = (.92 * math.cos(theta) + .17 * math.sin(2 * theta)) * upper
    if number == "22":
        dy *= CUSHION_TYPING_VERTICAL_SCALE
    moved = remap(sprite, np.stack((x - dx, y - dy), axis=-1))
    moved = moved * (1 - lock[:, :, None]) + anchor * lock[:, :, None]
    moved[:4] = moved[-4:] = moved[:, :4] = moved[:, -4:] = 0
    return unpremultiply(moved)


def render_motion(source, destination, atlas_path):
    number = source.name.split("-", 1)[0]
    if number in SESSION_SCENES:
        poses, anchor_mask, bounds = session_poses(source)
        sprites, grid, ground, lock = prepare(poses, anchor_mask, bounds)
        sequence = session_sequence(number)
        anchor = sprites[0]
        if number == "22":
            # Reduce the authored pose displacement as well as the procedural bob.
            free = 1 - cv2.GaussianBlur(lock, (0, 0), 2)
            neutral_features = features(anchor)
            for index in range(1, len(sprites)):
                sprite = sprites[index]
                flow = estimate_flow(features(sprite), neutral_features)
                correction = np.zeros_like(flow)
                correction[:, :, 1] = flow[:, :, 1] * (1 - CUSHION_TYPING_VERTICAL_SCALE) * free
                sprites[index] = remap(sprite, sampling_for(grid, correction, 1))
    else:
        poses, durations = timeline(source)
        poses = registered_poses(poses, number)
        if number in {"06", "07"}:
            # Return through bent knees before reversing into the standing opening.
            poses.append(poses[1])
            durations.append(210)
        sprites, grid, ground, _ = prepare(poses)
        lock, anchor = lock_contacts(sprites, grid, ground, number)
        sequence = list(enumerate(durations))
    stages, durations = zip(*sequence)
    transitions = list(zip(stages, (*stages[1:], stages[0])))
    flows = {
        (start, end): estimated_pair(sprites[start], sprites[end], grid, source.name)
        for start, end in set(transitions) if start != end
    }
    locked_mask = lock >= 1
    ends = np.cumsum(durations)
    original_ms = sum(durations)
    width, height = sprites[0].shape[1], sprites[0].shape[0]
    atlas = Image.new("RGBA", (width * ATLAS_COLUMNS, height * math.ceil(ATLAS_FRAMES / ATLAS_COLUMNS)))
    frames = []
    for idx in range(ATLAS_FRAMES):
        phase = idx / ATLAS_FRAMES
        # Walk three times in place, while the other clips play their full action once.
        t = ((phase * 3) % 1 if number == "05" else phase) * original_ms
        current = min(len(ends) - 1, int(np.searchsorted(ends, t, side="right")))
        remaining = float(ends[current]) - t
        budget = min(225, durations[current] * (.88 if number == "05" else .70))
        start, end = transitions[current]
        frame = sprites[start]
        if remaining < budget and start != end:
            frame = inbetween(frame, sprites[end],
                              grid, flows[start, end], 1 - remaining / budget,
                              single_pose=number in {"03", "06", "07"})
        frame = pose_motion(frame, grid, phase, number, lock, anchor)
        atlas.paste(frame, (idx % ATLAS_COLUMNS * width, idx // ATLAS_COLUMNS * height))
        if idx % (ATLAS_FRAMES // FRAME_COUNT) == 0:
            frames.append(frame)

    boundaries = [round(i * 1000 / FPS) for i in range(FRAME_COUNT + 1)]
    durations = [stop - start for start, stop in zip(boundaries, boundaries[1:])]
    frames[0].save(destination, lossless=True, method=1, save_all=True, append_images=frames[1:],
                   loop=0, duration=durations)
    atlas.save(atlas_path, lossless=True, method=1, exact=True)

    with Image.open(destination) as clip:
        assert clip.n_frames == FRAME_COUNT and clip.info["loop"] == 0, (source, clip.n_frames)
        actual, pixels_seen = [], set()
        for j in range(clip.n_frames):
            clip.seek(j)
            pixels = np.array(clip.convert("RGBA"))
            pixels[pixels[:, :, 3] == 0] = 0
            assert pixels[:, :, 3].min() == 0 and pixels[:, :, 3].max() == 255
            if j == 0:
                first_contact = pixels[locked_mask].tobytes()
            assert pixels[locked_mask].tobytes() == first_contact, (source, j)
            pixels_seen.add(sha256(pixels.tobytes()).digest())
            actual.append(clip.info["duration"])
        assert sum(actual) == DURATION_MS and set(actual) == {16, 17}
        unique = len(pixels_seen)

    with Image.open(atlas_path) as check:
        assert check.size == atlas.size and check.mode == "RGBA"
        # Decode the first and final tile to catch an incomplete output.
        j = ATLAS_FRAMES - 1
        for i in (0, j):
            left, top = i % ATLAS_COLUMNS * width, i // ATLAS_COLUMNS * height
            tile = check.crop((left, top, left + width, top + height))
            assert tile.getchannel("A").getbbox() is not None

    return {
        "WebP": destination.relative_to(root).as_posix(), "目标帧率": FPS,
        "解码帧数": FRAME_COUNT, "独立画面数": unique, "时长毫秒": DURATION_MS,
        "大小": [width, height], "单帧时长范围毫秒": [16, 17],
        "锚定": "固定画布与支点" if locked_mask.any() else "固定画布，局部姿势运动",
    }, {
        "图集": atlas_path.relative_to(root).as_posix(), "基准时长毫秒": DURATION_MS,
        "默认速度百分比": 100, "速度范围百分比": [MIN_SPEED, MAX_SPEED],
        "图集帧数": ATLAS_FRAMES, "图集列数": ATLAS_COLUMNS, "帧大小": [width, height],
    }


def build(action):
    source = source_path(action)
    destination = output / (source.stem + ".webp")
    atlas = output / (source.stem + "-frames.webp")
    metrics, speed = render_motion(source, destination, atlas)
    print(f"{source.name[:2]}: {metrics['解码帧数']} frames, {metrics['独立画面数']} unique, {metrics['时长毫秒']} ms", flush=True)
    return action, metrics, speed


def source_path(action):
    return root / (action.get("关键帧") or action["GIF"])


def main():
    output.mkdir(parents=True, exist_ok=True)
    path = root / "action-catalog.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    selection = set(sys.argv[1:])
    actions = [a for episode in data["分集记录"] for a in episode["动作"]]
    actions.extend(data.get("仓库动作", []))
    actions.sort(key=source_path)
    if selection:
        actions = [a for a in actions if source_path(a).name[:2] in selection]
    if not actions:
        raise ValueError("No desktop-pet motions selected")
    with ThreadPoolExecutor(max_workers=min(4, len(actions))) as pool:
        for action, metrics, speed in pool.map(build, actions):
            action["60帧流畅版"] = metrics
            action["可调速预览"] = speed
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    temp.replace(path)


if __name__ == "__main__":
    main()
