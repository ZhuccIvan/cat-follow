from pathlib import Path
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from build_assets import fit_to_cell, key_background


def rendered_sample_alpha(sample_name: str) -> np.ndarray:
    source = Image.open(ROOT / "workframes" / sample_name)
    rendered = fit_to_cell(key_background(source))
    return np.array(rendered.getchannel("A"))


def rendered_sample_rgba(sample_name: str) -> np.ndarray:
    source = Image.open(ROOT / "workframes" / sample_name)
    rendered = fit_to_cell(key_background(source))
    return np.array(rendered)


def test_front_frame_keeps_lower_body_between_feet() -> None:
    alpha = rendered_sample_alpha("sample_002.png")
    lower_center = alpha[365:450, 220:292]

    transparent_ratio = float((lower_center == 0).mean())

    assert transparent_ratio < 0.01


def test_front_frame_keeps_visible_tail_mass() -> None:
    alpha = rendered_sample_alpha("sample_002.png")
    tail = alpha[330:450, 360:455]

    opaque_ratio = float((tail > 0).mean())

    assert opaque_ratio > 0.39


def test_front_frame_uses_source_pixels_for_repaired_gap() -> None:
    rgba = rendered_sample_rgba("sample_002.png")
    red, green, blue, alpha = rgba[400, 260]

    assert alpha == 255
    assert red < 220
    assert abs(int(red) - int(green)) < 80


def test_front_frame_has_no_semitransparent_lower_body_stripes() -> None:
    rgba = rendered_sample_rgba("sample_002.png")
    alpha = rgba[330:455, 110:430, 3]

    semitransparent = (alpha > 0) & (alpha < 255)

    assert int(semitransparent.sum()) < 20


if __name__ == "__main__":
    test_front_frame_keeps_lower_body_between_feet()
    test_front_frame_keeps_visible_tail_mass()
    test_front_frame_uses_source_pixels_for_repaired_gap()
    test_front_frame_has_no_semitransparent_lower_body_stripes()
    print("mask quality checks passed")
