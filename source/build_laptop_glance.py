"""Build quiet typing, a brief silent viewer glance."""

from PIL import Image, ImageDraw, ImageFilter

from build_laptop_work import (
    TYPE_DURATIONS,
    assert_patch,
    encode_motion,
    normalize,
    package_native,
    read_frames,
    remove_shoes,
    thinking_frames,
)
from build_pose_laptop import output_preview, tile
from build_upgrade import PROJECT, clear_transparent_rgb, render


BASE = "laptop-work-2026-11-20"
SOURCE = PROJECT / "source" / "laptop-glance"
OUTPUT = PROJECT / "build" / "laptop-glance"
GLANCE_HOLDS = (300, 450, 600, 180, 450, 620)
GLANCE_TRAVEL = (440, 480, 300, 420, 760)
FINGERTIPS = (
    ((80, 130), (91, 130), (96, 133), (95, 138), (90, 142), (81, 141), (78, 137)),
    ((94, 135), (103, 133), (110, 134), (113, 138), (109, 145), (98, 145), (92, 141)),
)


def finger_mask(size):
    mask = Image.new("L", size)
    brush = ImageDraw.Draw(mask)
    for outline in FINGERTIPS:
        brush.polygon(outline, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(0.6))


def typing_poses(rest, references):
    mask = finger_mask(rest.size)
    poses = [rest]
    for source in references[1:5]:
        pose = Image.composite(source, rest, mask)
        clear_transparent_rgb(pose)
        assert_patch(rest, pose, mask, "Typing moved outside the fingertips and keys.")
        poses.append(pose)
    poses.append(rest)
    assert len({frame.tobytes() for frame in poses}) >= 5
    return poses


def main():
    prior = read_frames(PROJECT / "source" / "pose" / "frames" / "laptop")
    rest = remove_shoes(prior)[0]
    typing = typing_poses(rest, read_frames(SOURCE / "frames" / "fingers"))
    face, face_delays = thinking_frames(
        rest, read_frames(SOURCE / "frames" / "glance"), GLANCE_HOLDS, GLANCE_TRAVEL
    )
    fit = normalize(rest)
    tap_cells = [fit(frame) for frame in typing]
    head_cells = [fit(frame) for frame in face]
    lower = head_cells[0].crop((0, 128, 192, 208)).tobytes()
    assert all(frame.crop((0, 128, 192, 208)).tobytes() == lower for frame in head_cells)

    package_native(tap_cells, output=OUTPUT, base=BASE)
    strip = Image.new("RGBA", (6 * 192, 208))
    tile(strip, 0, tap_cells)
    strip.save(OUTPUT / "laptop-strip.webp", lossless=True, exact=True, method=6)
    encode_motion(OUTPUT / "laptop-typing.webp", tap_cells, TYPE_DURATIONS)
    encode_motion(OUTPUT / "laptop-thinking.webp", head_cells, face_delays)
    output_preview(OUTPUT / "laptop-typing.gif", tap_cells, TYPE_DURATIONS)
    output_preview(OUTPUT / "laptop-seated-thinking.gif", head_cells, face_delays)

    contact = Image.new("RGB", (6 * 192, 2 * 208), "#222831")
    for row, cells in enumerate((tap_cells, head_cells[::5])):
        for col, cell in enumerate(cells):
            contact.paste(render(cell), (col * 192, row * 208))
    contact.save(OUTPUT / "laptop-glance-frames.png")


if __name__ == "__main__":
    main()
