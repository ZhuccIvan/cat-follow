from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")


def test_reset_zone_is_subject_center_specific() -> None:
    assert "function isInSubjectResetZone" in HTML
    assert "RESET_ZONE_CENTER_X" in HTML
    assert "RESET_ZONE_CENTER_Y" in HTML


def test_reset_zone_no_longer_uses_generic_canvas_distance() -> None:
    assert "distance < rect.width * 0.12" not in HTML
    assert "Math.hypot(dx, dy)" not in HTML


if __name__ == "__main__":
    test_reset_zone_is_subject_center_specific()
    test_reset_zone_no_longer_uses_generic_canvas_distance()
    print("reset zone checks passed")
