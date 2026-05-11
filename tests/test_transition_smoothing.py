from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")


def test_frontend_does_not_use_fractional_frame_smoothing() -> None:
    assert "SMOOTHING_HALFLIFE_MS" not in HTML
    assert "currentFrameFloat" not in HTML
    assert "drawInterpolatedFrame" not in HTML


def test_frontend_does_not_crossfade_neighboring_frames() -> None:
    assert "ctx.globalAlpha = 1 - blend" not in HTML
    assert "ctx.globalAlpha = blend" not in HTML


if __name__ == "__main__":
    test_frontend_does_not_use_fractional_frame_smoothing()
    test_frontend_does_not_crossfade_neighboring_frames()
    print("no transition smoothing checks passed")
