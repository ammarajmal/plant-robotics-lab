from __future__ import annotations

import math
from pathlib import Path

import pytest

from plant_robotics.tracking.blue_marker import TrackRow
from plant_robotics.tracking.evaluation import GroundTruth, evaluate, load_ground_truth


def _row(frame: int, x: float, y: float, valid: bool = True) -> TrackRow:
    return TrackRow(frame, x, y, "VISIBLE" if valid else "PREDICTED", "m", valid)


def test_perfect_track_scores_zero_error() -> None:
    truth = [GroundTruth(i, 10.0 * i, 5.0, 2) for i in range(5)]
    result = evaluate([_row(i, 10.0 * i, 5.0) for i in range(5)], truth)
    assert result["mean_position_error_px"] == 0.0
    assert result["success_rate_at_20px"] == 1.0
    assert result["false_valid_rate"] == 0.0


def test_valid_while_occluded_counts_as_false_valid() -> None:
    truth = [GroundTruth(0, 1.0, 1.0, 2), GroundTruth(1, math.nan, math.nan, 0)]
    result = evaluate([_row(0, 1.0, 1.0), _row(1, 1.0, 1.0)], truth)
    assert result["false_valid_rate"] == 0.5
    assert result["n_scored_visible"] == 1


def test_far_valid_prediction_fails_threshold() -> None:
    result = evaluate([_row(0, 100.0, 0.0)], [GroundTruth(0, 0.0, 0.0, 2)])
    assert result["success_rate_at_20px"] == 0.0
    assert result["false_valid_rate"] == 1.0


def test_lost_track_has_no_position_and_is_not_a_success() -> None:
    lost = TrackRow(0, math.nan, math.nan, "LOST", "none", False)
    result = evaluate([lost], [GroundTruth(0, 5.0, 5.0, 2)])
    assert result["n_without_position"] == 1
    assert result["success_rate_at_20px"] == 0.0


def test_loader_validates(tmp_path: Path) -> None:
    good = tmp_path / "g.csv"
    good.write_text("frame,x,y,w,h,visibility,notes\n3,1.5,2.5,4,4,2,\n9,,,,,0,occluded\n")
    assert [g.visibility for g in load_ground_truth(good)] == [2, 0]
    bad = tmp_path / "b.csv"
    bad.write_text("frame,x,y,w,h,visibility,notes\n3,,,,,2,\n")
    with pytest.raises(ValueError):
        load_ground_truth(bad)
