from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build_assets


def read_index_html() -> str:
    return (ROOT / "index.html").read_text(encoding="utf-8")


def index_number_constant(name: str) -> int:
    match = re.search(rf"const\s+{name}\s*=\s*(\d+);", read_index_html())
    assert match, f"{name} not found"
    return int(match.group(1))


def test_assets_sample_enough_video_frames() -> None:
    assert build_assets.SAMPLE_STEP <= 4


def test_frontend_declares_dense_sprite_frame_count() -> None:
    assert index_number_constant("FRAME_COUNT") >= 60


def test_sprite_columns_fit_webp_dimension_limit() -> None:
    assert build_assets.SPRITE_COLUMNS * build_assets.FRAME_SIZE <= 16383


if __name__ == "__main__":
    test_assets_sample_enough_video_frames()
    test_frontend_declares_dense_sprite_frame_count()
    test_sprite_columns_fit_webp_dimension_limit()
    print("frame density checks passed")
