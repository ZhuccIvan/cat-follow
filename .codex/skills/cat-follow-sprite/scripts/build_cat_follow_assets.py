from __future__ import annotations

import argparse
import json
import math
import subprocess
from collections import deque
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def run_ffmpeg(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-y", *args], check=True)


def extract_frames(video: Path, work_dir: Path, sample_step: int, max_source_frame: int | None) -> list[Path]:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    sample_dir = work_dir / f"samples_step_{sample_step}_{stamp}"
    sample_dir.mkdir(parents=True, exist_ok=False)
    pattern = str(sample_dir / "sample_%03d.png")
    selector = f"not(mod(n,{sample_step}))"
    if max_source_frame is not None:
        selector = f"lte(n,{max_source_frame})*{selector}"
    run_ffmpeg(
        [
            "-i",
            str(video),
            "-map",
            "0:v:0",
            "-vf",
            f"select='{selector}'",
            "-fps_mode",
            "passthrough",
            pattern,
        ]
    )
    return sorted(sample_dir.glob("sample_*.png"))


def make_contact_sheet(files: list[Path], out_path: Path, sample_step: int, thumb: int) -> None:
    cols = 6
    rows = math.ceil(len(files) / cols)
    sheet = Image.new("RGB", (cols * thumb, rows * thumb), (28, 28, 28))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", max(12, thumb // 10))
    except OSError:
        font = ImageFont.load_default()

    for i, path in enumerate(files):
        img = Image.open(path).convert("RGB").resize((thumb, thumb), Image.Resampling.LANCZOS)
        x = i % cols * thumb
        y = i // cols * thumb
        sheet.paste(img, (x, y))
        label = f"{i * sample_step:03d}"
        draw.rectangle((x + 4, y + 4, x + 58, y + 30), fill=(0, 0, 0))
        draw.text((x + 8, y + 7), label, fill=(255, 255, 255), font=font)
    sheet.save(out_path)


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
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w:
                add(ny, nx)
    return seen


def subject_components(mask: np.ndarray) -> np.ndarray:
    h, w = mask.shape
    seen = np.zeros((h, w), dtype=bool)
    components: list[tuple[int, int, int, int, int, list[tuple[int, int]]]] = []

    for start_y in range(h):
        for start_x in np.flatnonzero(mask[start_y] & ~seen[start_y]):
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
    expanded = (max(0, x1 - 42), max(0, y1 - 28), min(w - 1, x2 + 42), min(h - 1, y2 + 32))

    for area, cx1, cy1, cx2, cy2, pixels in components:
        center_x = (cx1 + cx2) / 2
        center_y = (cy1 + cy2) / 2
        inside = expanded[0] <= center_x <= expanded[2] and expanded[1] <= center_y <= expanded[3]
        if area == largest[0] or (area >= 24 and inside):
            ys, xs = zip(*pixels)
            keep[np.array(ys), np.array(xs)] = True
    return keep


def key_background(img: Image.Image) -> Image.Image:
    rgb = np.array(img.convert("RGB"))
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
    r, g, b = rgb_i[:, :, 0], rgb_i[:, :, 1], rgb_i[:, :, 2]
    greenish = (g > r + 15) & (g > b + 8) & (g > 90)
    bg_connected = flood_from_edges((dist < 58) | greenish)
    alpha = np.where(bg_connected, 0, 255).astype(np.uint8)
    alpha = np.where(subject_components(alpha > 0), 255, 0).astype(np.uint8)
    return Image.fromarray(np.dstack([rgb, alpha]))


def repair_lower_subject_gaps(img: Image.Image, frame_size: int) -> Image.Image:
    rgba = np.array(img.convert("RGBA"))
    alpha = rgba[:, :, 3]
    repaired = rgba.copy()
    min_y = round(frame_size * 0.56)
    max_gap = round(frame_size * 0.36)

    for y in range(min_y, frame_size):
        row_alpha = alpha[y]
        opaque = np.flatnonzero(row_alpha > 48)
        if len(opaque) < 2:
            continue
        start, end = int(opaque[0]), int(opaque[-1])
        if end - start < frame_size * 0.16:
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
            left, right = gap_start - 1, gap_end + 1
            if not (0 <= left < frame_size and right < frame_size):
                continue
            if row_alpha[left] <= 48 or row_alpha[right] <= 48 or gap_end - gap_start + 1 > max_gap:
                continue
            for gx in range(gap_start, gap_end + 1):
                r, g, b = [int(value) for value in repaired[y, gx, :3]]
                if not (g > r + 12 and g > b + 8 and g > 80) and r + g + b >= 26:
                    repaired[y, gx, 3] = 255
    return Image.fromarray(repaired)


def fit_to_cell(img: Image.Image, frame_size: int, scale: float, y_offset: int) -> Image.Image:
    source = img.convert("RGBA")
    target_size = (round(source.width * scale), round(source.height * scale))
    source_arr = np.array(source)
    rgb = Image.fromarray(source_arr[:, :, :3]).resize(target_size, Image.Resampling.LANCZOS)
    alpha = source.getchannel("A").resize(target_size, Image.Resampling.LANCZOS)
    resized = Image.merge("RGBA", (*rgb.split(), alpha))
    cell = Image.new("RGBA", (frame_size, frame_size), (0, 0, 0, 0))
    cell.paste(resized, ((frame_size - resized.width) // 2, y_offset))
    repaired = repair_lower_subject_gaps(cell, frame_size)
    arr = np.array(repaired.convert("RGBA"))
    arr[:, :, 3] = np.where(arr[:, :, 3] > 48, 255, 0).astype(np.uint8)
    return Image.fromarray(arr)


def build_sprite(
    files: list[Path],
    out_dir: Path,
    frame_size: int,
    sprite_columns: int,
    scale: float,
    y_offset: int,
    front_source_frame: int,
    sample_step: int,
) -> dict[str, object]:
    frames = [fit_to_cell(key_background(Image.open(path)), frame_size, scale, y_offset) for path in files]
    rows = math.ceil(len(frames) / sprite_columns)
    sprite = Image.new("RGBA", (frame_size * sprite_columns, frame_size * rows), (0, 0, 0, 0))
    for i, frame in enumerate(frames):
        sprite.alpha_composite(frame, (i % sprite_columns * frame_size, i // sprite_columns * frame_size))
    sprite.save(out_dir / "sprite.webp", "WEBP", lossless=True, quality=100, method=6)

    front_index = min(len(frames) - 1, max(0, round(front_source_frame / sample_step)))
    frames[front_index].save(out_dir / "frame_front.webp", "WEBP", lossless=True, quality=100, method=6)
    return {
        "frame_count": len(frames),
        "frame_size": frame_size,
        "sprite_columns": sprite_columns,
        "sprite_size": [sprite.width, sprite.height],
        "front_index": front_index,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--sample-step", type=int, default=4)
    parser.add_argument("--max-source-frame", type=int, default=None)
    parser.add_argument("--frame-size", type=int, default=512)
    parser.add_argument("--sprite-columns", type=int, default=16)
    parser.add_argument("--scale", type=float, default=0.64)
    parser.add_argument("--y-offset", type=int, default=34)
    parser.add_argument("--front-source-frame", type=int, default=8)
    parser.add_argument("--contact-thumb", type=int, default=180)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.sprite_columns * args.frame_size > 16383:
        raise ValueError("sprite columns * frame size exceeds WebP 16383px dimension limit")
    files = extract_frames(args.video, args.out / "workframes", args.sample_step, args.max_source_frame)
    make_contact_sheet(files, args.out / "contact_sheet_labeled.png", args.sample_step, args.contact_thumb)
    report = build_sprite(
        files,
        args.out,
        args.frame_size,
        args.sprite_columns,
        args.scale,
        args.y_offset,
        args.front_source_frame,
        args.sample_step,
    )
    report.update({"video": str(args.video), "sample_step": args.sample_step})
    (args.out / "asset_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
