from __future__ import annotations

import math
import subprocess
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent
VIDEO = ROOT / "生成指定猫咪动作的视频.mp4"
WORK = ROOT / "workframes"
SAMPLE_STEP = 4
FRAME_SIZE = 512
CONTACT_THUMB = 180
FRONT_SOURCE_FRAME = 8
SPRITE_COLUMNS = 16


def run_ffmpeg(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-y", *args], check=True)


def extract_sample_frames() -> list[Path]:
    WORK.mkdir(exist_ok=True)
    pattern = str(WORK / "sample_%03d.png")
    run_ffmpeg(
        [
            "-i",
            str(VIDEO),
            "-map",
            "0:v:0",
            "-vf",
            f"select='not(mod(n,{SAMPLE_STEP}))'",
            "-fps_mode",
            "passthrough",
            pattern,
        ]
    )
    return sorted(WORK.glob("sample_*.png"))


def make_contact_sheet(files: list[Path]) -> None:
    cols = 6
    rows = math.ceil(len(files) / cols)
    sheet = Image.new("RGB", (cols * CONTACT_THUMB, rows * CONTACT_THUMB), (28, 28, 28))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 18)
    except OSError:
        font = ImageFont.load_default()

    for i, path in enumerate(files):
        img = Image.open(path).convert("RGB").resize(
            (CONTACT_THUMB, CONTACT_THUMB), Image.Resampling.LANCZOS
        )
        x = i % cols * CONTACT_THUMB
        y = i // cols * CONTACT_THUMB
        sheet.paste(img, (x, y))
        label = f"{i * SAMPLE_STEP:03d}"
        draw.rectangle((x + 4, y + 4, x + 58, y + 30), fill=(0, 0, 0))
        draw.text((x + 8, y + 7), label, fill=(255, 255, 255), font=font)

    sheet.save(ROOT / "contact_sheet_labeled.png")


def flood_from_edges(candidate: np.ndarray) -> np.ndarray:
    h, w = candidate.shape
    seen = np.zeros((h, w), dtype=bool)
    queue: deque[tuple[int, int]] = deque()

    def add(y: int, x: int) -> None:
        if candidate[y, x] and not seen[y, x]:
            seen[y, x] = True
            queue.append((y, x))

    for x in range(w):
        add(0, x)
        add(h - 1, x)
    for y in range(h):
        add(y, 0)
        add(y, w - 1)

    while queue:
        y, x = queue.popleft()
        if y > 0:
            add(y - 1, x)
        if y + 1 < h:
            add(y + 1, x)
        if x > 0:
            add(y, x - 1)
        if x + 1 < w:
            add(y, x + 1)

    return seen


def largest_component(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=bool)
    best: list[tuple[int, int]] = []

    for start_y in range(h):
        row_candidates = np.flatnonzero(mask[start_y] & ~seen[start_y])
        for start_x in row_candidates:
            if seen[start_y, start_x]:
                continue
            component: list[tuple[int, int]] = []
            queue: deque[tuple[int, int]] = deque([(start_y, int(start_x))])
            seen[start_y, start_x] = True
            while queue:
                y, x = queue.popleft()
                component.append((y, x))
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        queue.append((ny, nx))
            if len(component) > len(best):
                best = component

    keep = np.zeros((h, w), dtype=bool)
    if best:
        ys, xs = zip(*best)
        keep[np.array(ys), np.array(xs)] = True
    return keep


def subject_components(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=bool)
    components: list[tuple[int, int, int, int, int, list[tuple[int, int]]]] = []

    for start_y in range(h):
        row_candidates = np.flatnonzero(mask[start_y] & ~seen[start_y])
        for start_x in row_candidates:
            if seen[start_y, start_x]:
                continue

            pixels: list[tuple[int, int]] = []
            queue: deque[tuple[int, int]] = deque([(start_y, int(start_x))])
            seen[start_y, start_x] = True
            while queue:
                y, x = queue.popleft()
                pixels.append((y, x))
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        queue.append((ny, nx))

            ys = [p[0] for p in pixels]
            xs = [p[1] for p in pixels]
            components.append((len(pixels), min(xs), min(ys), max(xs), max(ys), pixels))

    keep = np.zeros((h, w), dtype=bool)
    if not components:
        return keep

    largest = max(components, key=lambda item: item[0])
    _, x1, y1, x2, y2, _ = largest
    expanded = (
        max(0, x1 - 42),
        max(0, y1 - 28),
        min(w - 1, x2 + 42),
        min(h - 1, y2 + 32),
    )

    for area, cx1, cy1, cx2, cy2, pixels in components:
        center_x = (cx1 + cx2) / 2
        center_y = (cy1 + cy2) / 2
        inside_subject_box = (
            expanded[0] <= center_x <= expanded[2] and expanded[1] <= center_y <= expanded[3]
        )
        if area == largest[0] or (area >= 24 and inside_subject_box):
            ys, xs = zip(*pixels)
            keep[np.array(ys), np.array(xs)] = True

    return keep


def key_background(img: Image.Image) -> Image.Image:
    rgb = np.array(img.convert("RGB"))
    h, w, _ = rgb.shape
    edge = 18
    border = np.concatenate(
        [
            rgb[:edge, :, :].reshape(-1, 3),
            rgb[-edge:, :, :].reshape(-1, 3),
            rgb[:, :edge, :].reshape(-1, 3),
            rgb[:, -edge:, :].reshape(-1, 3),
        ],
        axis=0,
    )
    bg = np.median(border, axis=0)
    rgb_i = rgb.astype(np.int16)
    dist = np.sqrt(np.sum((rgb_i - bg.astype(np.int16)) ** 2, axis=2))
    r = rgb_i[:, :, 0]
    g = rgb_i[:, :, 1]
    b = rgb_i[:, :, 2]

    # Background is discovered from edge-connected green/mint pixels only.
    # This protects white fur, gray shadows, eye highlights, and other subject details.
    greenish = (g > r + 15) & (g > b + 8) & (g > 90)
    candidate_bg = (dist < 58) | greenish
    bg_connected = flood_from_edges(candidate_bg)

    alpha = np.where(bg_connected, 0, 255).astype(np.uint8)
    keep = subject_components(alpha > 0)
    alpha = np.where(keep, 255, 0).astype(np.uint8)

    rgba = np.dstack([rgb, alpha])
    return Image.fromarray(rgba, "RGBA")


def fit_to_cell(img: Image.Image) -> Image.Image:
    scale = 0.64
    source = img.convert("RGBA")
    target_size = (round(source.width * scale), round(source.height * scale))
    source_arr = np.array(source)
    rgb = Image.fromarray(source_arr[:, :, :3], "RGB").resize(
        target_size, Image.Resampling.LANCZOS
    )
    alpha = source.getchannel("A").resize(target_size, Image.Resampling.LANCZOS)
    resized = Image.merge("RGBA", (*rgb.split(), alpha))
    cell = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    x = (FRAME_SIZE - resized.width) // 2
    y = 34
    # Direct paste keeps RGB values for pixels whose alpha was keyed to zero.
    # The lower-gap repair can then restore original video pixels without
    # inventing striped/interpolated colors.
    cell.paste(resized, (x, y))
    return solid_subject_alpha(repair_lower_subject_gaps(cell))


def solid_subject_alpha(img: Image.Image) -> Image.Image:
    rgba = np.array(img.convert("RGBA"))
    rgba[:, :, 3] = np.where(rgba[:, :, 3] > 48, 255, 0).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def repair_lower_subject_gaps(img: Image.Image) -> Image.Image:
    rgba = np.array(img.convert("RGBA"))
    alpha = rgba[:, :, 3]
    repaired = rgba.copy()
    min_y = round(FRAME_SIZE * 0.56)
    max_gap = round(FRAME_SIZE * 0.36)

    for y in range(min_y, FRAME_SIZE):
        row_alpha = alpha[y]
        opaque = np.flatnonzero(row_alpha > 48)
        if len(opaque) < 2:
            continue

        start = int(opaque[0])
        end = int(opaque[-1])
        if end - start < FRAME_SIZE * 0.16:
            continue

        x = start
        while x <= end:
            if row_alpha[x] > 48:
                x += 1
                continue

            gap_start = x
            while x <= end and row_alpha[x] <= 48:
                x += 1
            gap_end = x - 1
            gap_width = gap_end - gap_start + 1
            left = gap_start - 1
            right = gap_end + 1

            if (
                0 <= left < FRAME_SIZE
                and right < FRAME_SIZE
                and row_alpha[left] > 48
                and row_alpha[right] > 48
                and gap_width <= max_gap
            ):
                for gx in range(gap_start, gap_end + 1):
                    r, g, b = [int(value) for value in repaired[y, gx, :3]]
                    greenish_background = g > r + 12 and g > b + 8 and g > 80
                    very_dark_edge = r + g + b < 26
                    if not greenish_background and not very_dark_edge:
                        repaired[y, gx, 3] = 255

    return Image.fromarray(repaired, "RGBA")


def build_sprite(files: list[Path]) -> None:
    frames = [fit_to_cell(key_background(Image.open(path))) for path in files]
    rows = math.ceil(len(frames) / SPRITE_COLUMNS)
    sprite = Image.new(
        "RGBA", (FRAME_SIZE * SPRITE_COLUMNS, FRAME_SIZE * rows), (0, 0, 0, 0)
    )
    for i, frame in enumerate(frames):
        x = i % SPRITE_COLUMNS * FRAME_SIZE
        y = i // SPRITE_COLUMNS * FRAME_SIZE
        sprite.alpha_composite(frame, (x, y))

    sprite.save(ROOT / "sprite.webp", "WEBP", lossless=True, quality=100, method=6)
    front_index = FRONT_SOURCE_FRAME // SAMPLE_STEP
    frames[front_index].save(ROOT / "frame_front.webp", "WEBP", lossless=True, quality=100, method=6)


def main() -> None:
    files = extract_sample_frames()
    make_contact_sheet(files)
    build_sprite(files)
    print(f"sampled_frames={len(files)}")
    print(f"sprite={ROOT / 'sprite.webp'}")
    print(f"frame_front={ROOT / 'frame_front.webp'}")
    print(f"contact_sheet={ROOT / 'contact_sheet_labeled.png'}")


if __name__ == "__main__":
    main()
