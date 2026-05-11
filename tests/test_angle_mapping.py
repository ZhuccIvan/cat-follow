from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")


def number_constant(name: str) -> int:
    match = re.search(rf"const\s+{name}\s*=\s*(\d+);", HTML)
    assert match, f"{name} not found"
    return int(match.group(1))


def angle_keys() -> list[tuple[int, int]]:
    return [
        (int(angle), int(frame))
        for angle, frame in re.findall(r"angle:\s*(-?\d+),\s*frame:\s*(\d+)", HTML)
    ]


FRAME_COUNT = number_constant("FRAME_COUNT")
CENTER_FRAME = number_constant("CENTER_FRAME")
ANGLE_KEYS = angle_keys()
RIGHT_TOP_MATCH = re.search(r"RIGHT_TOP_KEY\s*=\s*\{\s*angle:\s*(-?\d+),\s*frame:\s*(\d+)", HTML)
RIGHT_TOP_KEY = (int(RIGHT_TOP_MATCH.group(1)), int(RIGHT_TOP_MATCH.group(2)))


def wrap_frame_distance(start: int, end: int) -> int:
    raw = end - start
    forward = (raw + FRAME_COUNT) % FRAME_COUNT
    backward = forward - FRAME_COUNT
    return forward if abs(forward) <= abs(backward) else backward


def normalize_angle(angle: float) -> float:
    value = ((angle + 180) % 360 + 360) % 360 - 180
    return 180 if value == -180 else value


def calibrated_frame_for_angle(angle: float) -> int:
    a = normalize_angle(angle)
    if a > -90 and a <= -45:
        start_angle, start_frame = RIGHT_TOP_KEY
        end_angle, end_frame = ANGLE_KEYS[3]
        t = (a - start_angle) / (end_angle - start_angle)
        span = wrap_frame_distance(start_frame, end_frame)
        return round((start_frame + span * t + FRAME_COUNT) % FRAME_COUNT)
    for (start_angle, start_frame), (end_angle, end_frame) in zip(ANGLE_KEYS, ANGLE_KEYS[1:]):
        if start_angle <= a <= end_angle:
            t = (a - start_angle) / (end_angle - start_angle)
            span = wrap_frame_distance(start_frame, end_frame)
            return round((start_frame + span * t + FRAME_COUNT) % FRAME_COUNT)
    return CENTER_FRAME


def test_calibrated_cardinal_and_diagonal_frames() -> None:
    assert CENTER_FRAME == 2
    assert calibrated_frame_for_angle(-90) == 56
    assert calibrated_frame_for_angle(0) == 22
    assert calibrated_frame_for_angle(90) == 34
    assert calibrated_frame_for_angle(180) == 42
    assert calibrated_frame_for_angle(-135) == 48
    assert calibrated_frame_for_angle(135) == 40


def test_left_upper_to_top_does_not_reset_to_front_frames() -> None:
    reset_like_frames = {0, 1, 2, 3, 4}
    for angle in range(-130, -89, 5):
        assert calibrated_frame_for_angle(angle) not in reset_like_frames


def test_right_upper_to_top_does_not_reset_to_front_frames() -> None:
    reset_like_frames = {0, 1, 2, 3, 4}
    for angle in range(-85, -44, 5):
        assert calibrated_frame_for_angle(angle) not in reset_like_frames


if __name__ == "__main__":
    test_calibrated_cardinal_and_diagonal_frames()
    test_left_upper_to_top_does_not_reset_to_front_frames()
    test_right_upper_to_top_does_not_reset_to_front_frames()
    print("angle mapping checks passed")
