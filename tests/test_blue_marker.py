from __future__ import annotations

import math

import numpy as np
import pytest

from plant_robotics.tracking.blue_marker import TrackerConfig, detect, run_baseline

SIZE = (120, 160)  # height, width


def _frame(center: tuple[int, int] | None) -> np.ndarray:
    image = np.full((*SIZE, 3), 30, dtype=np.uint8)
    if center is not None:
        x, y = center
        image[y - 5 : y + 5, x - 5 : x + 5] = (255, 0, 0)  # BGR blue
    return image


def _moving(count: int, step: int = 4):
    return [(i, _frame((20 + step * i, 60))) for i in range(count)]


def test_detects_blue_square_centroid() -> None:
    (cand,) = detect(_frame((50, 40)), TrackerConfig())
    assert math.hypot(cand.x - 49.5, cand.y - 39.5) < 1.0
    assert detect(_frame(None), TrackerConfig()) == []


def test_b0_tracks_and_rows_before_seed_are_uninitialized() -> None:
    rows = run_baseline(_moving(6), "b0", 2, (28, 60), 30.0)
    assert [r.state for r in rows[:2]] == ["UNINITIALIZED"] * 2
    assert all(r.state == "VISIBLE" and r.target_valid for r in rows[2:])
    assert math.isnan(rows[0].x)


def test_b1_lags_less_with_higher_process_noise() -> None:
    frames = _moving(40, step=3)

    def mean_error(q: float) -> float:
        rows = run_baseline(frames, "b1", 0, (20, 60), 30.0, TrackerConfig(process_noise=q))
        return float(np.mean([abs(r.x - (19.5 + 3 * r.frame)) for r in rows[10:]]))

    assert mean_error(10.0) < mean_error(1.0)


def test_b1_occlusion_state_progression_and_loss() -> None:
    frames = [(i, _frame((40, 60))) for i in range(3)] + [(i, _frame(None)) for i in range(3, 25)]
    rows = run_baseline(frames, "b1", 0, (40, 60), 30.0)
    assert rows[2].state == "VISIBLE"
    assert rows[3].state == "PARTIAL_OCCLUSION" and not rows[3].target_valid
    assert rows[5].state == "PREDICTED"
    assert rows[3 + 14].state == "LOST" and math.isnan(rows[3 + 14].x)


def test_far_blob_is_not_associated() -> None:
    rows = run_baseline([(0, _frame((140, 100)))], "b0", 0, (20, 20), 30.0)
    assert rows[0].state == "LOST"


@pytest.mark.parametrize("fps", [0.0, -1.0, float("nan")])
def test_invalid_fps_rejected(fps: float) -> None:
    with pytest.raises(ValueError):
        run_baseline([], "b1", 0, (0, 0), fps)


def test_config_rejects_bad_thresholds() -> None:
    with pytest.raises(ValueError):
        TrackerConfig(predicted_after_misses=20)
    with pytest.raises(ValueError):
        TrackerConfig(process_noise=0.0)
