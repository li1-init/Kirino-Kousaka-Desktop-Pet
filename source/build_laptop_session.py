"""Render the silent seated reaction from its six drawn poses."""

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


def make_reaction(poses, mask, fps):
    rest = poses[0]
    outside = mask.point(lambda value: 0 if value else 255)
    poses_and_delays = []
    for index, (pose, duration) in enumerate(zip(poses, HOLDS, strict=True)):
        poses_and_delays.append((pose, duration))
        if index < len(TRAVEL):
            travel = TRAVEL[index]
            count = round(travel * fps / 1000)
            boundaries = [round(step * travel / count) for step in range(count + 1)]
            for step, middle in enumerate(optical_inbetweens(pose, poses[index + 1], count, eased=True)):
                middle.paste(rest, mask=outside)
                poses_and_delays.append((middle, boundaries[step + 1] - boundaries[step]))
    normalize_pose = normalize(rest)
    fitted_rest = normalize_pose(rest)
    stationary_foreground = Image.new("L", fitted_rest.size)
    for outline in STATIONARY_FOREGROUND:
        ImageDraw.Draw(stationary_foreground).polygon(outline, fill=255)
    foreground_edge = stationary_foreground.filter(ImageFilter.GaussianBlur(1))
    frames, delays = [], []
    for pose, duration in poses_and_delays:
        clear_transparent_rgb(pose)
        assert_patch(rest, pose, mask, "A frame changed outside the upper body.")
        fitted = normalize_pose(pose)
        fitted = Image.composite(fitted_rest, fitted, foreground_edge)
        fitted.paste(fitted_rest, mask=stationary_foreground)
        clear_transparent_rgb(fitted)
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
    fit = normalize(rest)
    for index, pose in enumerate(poses):
        contact.paste(render(fit(pose)), (index * 192, 0))
    contact.save(OUTPUT / "coordinated-contact.png")
    print(f"{len(frames)} source frames, 5000 ms, matched typing-to-thinking rest pose.")


if __name__ == "__main__":
    main()
