"""Render the silent seated reaction from its six drawn poses."""

from PIL import Image, ImageDraw, ImageFilter

from build_laptop_work import assert_patch, encode_motion, normalize, read_frames, remove_shoes
from build_pose_laptop import optical_inbetweens, output_preview
from build_upgrade import PROJECT, clear_transparent_rgb, render


SOURCE = PROJECT / "source" / "laptop-session"
OUTPUT = PROJECT / "build" / "laptop-session"
HOLDS = (300, 450, 600, 180, 450, 620)
TRAVEL = (440, 480, 300, 420, 760)
# The edge follows the laptop lid and stays above the fingers and the desk.
UPPER_BODY = (
    (0, 0), (191, 0), (191, 145), (146, 146), (131, 140),
    (121, 133), (118, 124), (84, 123), (78, 99), (0, 95),
)


def main():
    rest = remove_shoes(read_frames(PROJECT / "source/pose/frames/laptop"))[0]
    drawings = read_frames(SOURCE / "frames" / "idle")
    mask = Image.new("L", rest.size)
    ImageDraw.Draw(mask).polygon(UPPER_BODY, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(2))
    outside = mask.point(lambda value: 0 if value else 255)
    poses = [rest, *[Image.composite(frame, rest, mask) for frame in drawings[1:5]], rest]
    poses_and_delays = []
    for index, (pose, duration) in enumerate(zip(poses, HOLDS, strict=True)):
        poses_and_delays.append((pose, duration))
        if index < len(TRAVEL):
            for middle in optical_inbetweens(pose, poses[index + 1], 4):
                middle.paste(rest, mask=outside)
                poses_and_delays.append((middle, TRAVEL[index] // 4))
    normalize_pose = normalize(rest)
    frames, delays = [], []
    for pose, duration in poses_and_delays:
        clear_transparent_rgb(pose)
        assert_patch(rest, pose, mask, "A frame changed outside the upper body.")
        frames.append(normalize_pose(pose))
        delays.append(duration)
    assert sum(delays) == 5000
    assert len({frame.crop((105, 117, 151, 133)).tobytes() for frame in frames}) > 6
    with Image.open(PROJECT / "runtime/laptop-typing.webp") as typing:
        typing_frames, typing_delays = [], []
        for index in range(typing.n_frames):
            typing.seek(index)
            typing_frames.append(typing.convert("RGBA"))
            typing_delays.append(typing.info["duration"])
    assert frames[0].tobytes() == frames[-1].tobytes() == typing_frames[0].tobytes()
    encode_motion(OUTPUT / "laptop-thinking.webp", frames, delays)
    output_preview(OUTPUT / "laptop-seated-thinking.gif", frames, delays)
    output_preview(OUTPUT / "laptop-task-silent.gif", typing_frames + frames + typing_frames,
                   typing_delays + delays + typing_delays)
    contact = Image.new("RGB", (1152, 208), "#222831")
    for index, index_frame in enumerate(range(0, 26, 5)):
        contact.paste(render(frames[index_frame]), (index * 192, 0))
    contact.save(OUTPUT / "coordinated-contact.png")
    print("26 silent frames; 5000 ms; typing and thinking use the same rest pose.")


if __name__ == "__main__":
    main()
