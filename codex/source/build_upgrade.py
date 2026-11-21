import json
import subprocess
from pathlib import Path
from statistics import median

from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image, ImageDraw


WORK = Path(__file__).resolve().parent
PROJECT = WORK.parent
OUTPUT = PROJECT / "build"
BACKUP = PROJECT / "archive" / "pre-upgrade" / "active-account.png"
CELL_WIDTH, CELL_HEIGHT = 192, 208
ROWS = [
    ("idle", 6), ("right", 8), ("left", 8), ("waving", 4),
    ("jumping", 5), ("failed", 8), ("waiting", 6), ("running", 6),
    ("review", 6), ("look-1", 8), ("look-2", 8),
]
UPDATES = {"waving", "failed", "waiting", "running", "review"}
BRIEF_STATES = ("idle", "waving", "running", "waiting", "review", "failed")
BACKGROUND = "#222831"


def cell_box(row, column):
    x = column * CELL_WIDTH
    y = row * CELL_HEIGHT
    return x, y, x + CELL_WIDTH, y + CELL_HEIGHT


def landmarks(frame):
    alpha = frame.getchannel("A").point(lambda v: 255 if v >= 136 else 0)
    bottom = alpha.getbbox()[3]
    crown = alpha.crop((75, 0, 112, CELL_HEIGHT)).getbbox()[1]
    shoes = alpha.crop((0, bottom - 10, CELL_WIDTH, bottom)).getbbox()
    return crown, bottom, (shoes[0] + shoes[2]) / 2


def fit_frames(frames, idle):
    height = median(bottom - crown for crown, bottom, _ in map(landmarks, frames))
    idle_crown, idle_bottom, idle_shoes = landmarks(idle)
    scale = (idle_bottom - idle_crown) / height
    size = (round(CELL_WIDTH * scale), round(CELL_HEIGHT * scale))
    result = []
    for frame in frames:
        _, bottom, shoes = landmarks(frame)
        shifted = Image.new("RGBA", idle.size)
        resized = frame.resize(size, Image.Resampling.LANCZOS)
        position = (round(idle_shoes - shoes * size[0] / CELL_WIDTH),
                    round(idle_bottom - bottom * size[1] / CELL_HEIGHT))
        shifted.paste(resized, position)
        box = shifted.getchannel("A").getbbox()
        assert box and box[0] > 0 and box[1] > 0 and box[2] < CELL_WIDTH
        assert box[3] < CELL_HEIGHT
        result.append(shifted)
    return result


def clear_transparent_rgb(image):
    transparent = image.getchannel("A").point(lambda value: 255 if value == 0 else 0)
    image.paste((0, 0, 0, 0), mask=transparent)


def compose():
    original = Image.open(BACKUP).convert("RGBA")
    clear_transparent_rgb(original)
    atlas = original.copy()
    idle = original.crop(cell_box(0, 0))
    updates = {}
    for row, (state, count) in enumerate(ROWS):
        if state not in UPDATES:
            continue
        frames = [Image.open(path).convert("RGBA")
                  for path in sorted((WORK / "frames" / state).glob("*.png"))]
        assert len(frames) == count, (state, count, len(frames))
        updates[state] = fit_frames(frames, idle)
    updates["idle"] = [updates["review"][0]] * ROWS[0][1]
    for row, (state, count) in enumerate(ROWS):
        if state not in updates:
            continue
        atlas.paste((0, 0, 0, 0), (0, row * CELL_HEIGHT, atlas.width, (row + 1) * CELL_HEIGHT))
        for column, frame in enumerate(updates[state]):
            atlas.paste(frame, cell_box(row, column)[:2])
        positions = [landmarks(frame)[1:] for frame in updates[state]]
        assert max(abs(y - 192) for y, _ in positions) <= 2, (state, positions)
        assert max(abs(x - 98) for _, x in positions) <= 2, (state, positions)
        print(f"{state}: sole y, midpoint x: {positions}")

    package = OUTPUT / "kirino-chibi"
    package.mkdir(parents=True, exist_ok=True)
    atlas_path = package / "spritesheet.webp"
    clear_transparent_rgb(atlas)
    atlas.save(atlas_path, lossless=True, method=6, exact=True)
    encoded = Image.open(atlas_path).convert("RGBA")
    assert encoded.tobytes() == atlas.tobytes(), "Encoded sheet changed pixel data"
    for row, (state, count) in enumerate(ROWS):
        for column in range(8):
            box = cell_box(row, column)
            frame = encoded.crop(box)
            if state not in updates:
                assert frame.tobytes() == original.crop(box).tobytes(), (state, column)
            assert bool(frame.getchannel("A").getbbox()) == (column < count), (state, column)
    manifest = {
        "id": "kirino-chibi",
        "displayName": "高坂桐乃 Chibi",
        "description": "桐乃 Q 版宠物。待机时静止，处理任务时托腮思考，右上角带有气泡。",
        "spritesheetPath": "spritesheet.webp",
        "spriteVersionNumber": 2,
    }
    (package / "pet.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8")
    return encoded


def render(frame, scale=1):
    sprite = frame.resize((CELL_WIDTH * scale, CELL_HEIGHT * scale), Image.Resampling.LANCZOS)
    result = Image.new("RGB", sprite.size, BACKGROUND)
    result.paste(sprite, mask=sprite.getchannel("A"))
    return result


def previews(atlas):
    sequences = {name: [atlas.crop(cell_box(row, column)) for column in range(count)]
                 for row, (name, count) in enumerate(ROWS)}
    contact = Image.new("RGB", (8 * 128, len(BRIEF_STATES) * 152), BACKGROUND)
    labels = ImageDraw.Draw(contact)
    for row, state in enumerate(BRIEF_STATES):
        labels.text((9, row * 152 + 4), state, fill="white")
        frames = sequences[state][:1] if state == "idle" else sequences[state]
        for column, frame in enumerate(frames):
            contact.paste(render(frame).resize((126, 136), Image.Resampling.LANCZOS),
                          (column * 128, row * 152 + 15))
    contact.save(OUTPUT / "action-frames.png")

    thinking = [render(frame, scale=2) for frame in sequences["running"]]
    durations = [160, 160, 170, 100, 150, 260]
    palette = Image.new("RGB", (thinking[0].width * len(thinking), thinking[0].height))
    for column, frame in enumerate(thinking):
        palette.paste(frame, (column * frame.width, 0))
    indexed = [frame.quantize(palette=palette.quantize(colors=256), dither=Image.Dither.NONE)
               for frame in thinking] * 10
    gif = OUTPUT / "thinking-10s.gif"
    indexed[0].save(gif, save_all=True, append_images=indexed[1:], duration=durations * 10,
                    loop=0, disposal=2, optimize=False)
    with Image.open(gif) as preview:
        total = 0
        for index in range(preview.n_frames):
            preview.seek(index)
            total += preview.info["duration"]
        assert preview.n_frames == 60 and total == 10000

    # This preview uses the six actual atlas poses and stretches each cycle to one second.
    movie = OUTPUT / "thinking-10s.mp4"
    repeats = [10, 10, 10, 6, 9, 15]
    movie_bytes = b"".join(frame.tobytes() * n for frame, n in zip(thinking, repeats)) * 10
    subprocess.run([get_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
                    "-pixel_format", "rgb24", "-video_size", f"{2 * CELL_WIDTH}x{2 * CELL_HEIGHT}",
                    "-framerate", "60", "-i", "-", "-c:v", "libx264", "-crf", "18", "-pix_fmt",
                    "yuv420p", "-movflags", "+faststart", str(movie)], input=movie_bytes, check=True)


if __name__ == "__main__":
    previews(compose())
