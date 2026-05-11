from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")


def test_top_seam_transition_has_explicit_guard() -> None:
    assert "TOP_SEAM_LEFT_MIN" in HTML
    assert "TOP_SEAM_RIGHT_MAX" in HTML
    assert "function isTopSeamTransition" in HTML
    assert "function nextFrameTowards" in HTML


def test_regular_tick_uses_guarded_stepper() -> None:
    assert "currentFrame = nextFrameTowards(currentFrame, targetFrame);" in HTML
    assert "currentFrame + Math.sign(delta)" not in HTML


if __name__ == "__main__":
    test_top_seam_transition_has_explicit_guard()
    test_regular_tick_uses_guarded_stepper()
    print("top seam transition checks passed")
