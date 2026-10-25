"""Image-plane evaluation of seeded single-target tracks against sparse labels.

Only frames with a ground-truth row are scored. ``visibility``: 2 fully
visible, 1 partially visible, 0 occluded (no position expected). Identity
switches and occlusion recovery are NOT computed here (single-target, no IDs).
"""

from __future__ import annotations

import csv
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from plant_robotics.tracking.blue_marker import TrackRow


@dataclass(frozen=True)
class GroundTruth:
    frame: int
    x: float
    y: float
    visibility: int


def load_ground_truth(path: Path) -> list[GroundTruth]:
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            visibility = int(row["visibility"])
            if visibility not in (0, 1, 2):
                raise ValueError(f"visibility must be 0, 1 or 2, got {visibility}")
            x = float(row["x"]) if row["x"] != "" else math.nan
            y = float(row["y"]) if row["y"] != "" else math.nan
            if visibility > 0 and not (math.isfinite(x) and math.isfinite(y)):
                raise ValueError(f"frame {row['frame']}: visible label needs x and y")
            rows.append(GroundTruth(int(row["frame"]), x, y, visibility))
    return rows


def evaluate(
    track: Sequence[TrackRow], truth: Sequence[GroundTruth], threshold_px: float = 20.0
) -> dict[str, float | int]:
    by_frame = {r.frame: r for r in track}
    errors: list[float] = []
    successes: list[bool] = []
    valid_declared = false_valid = 0
    for gt in truth:
        row = by_frame.get(gt.frame)
        if row is None or row.state == "UNINITIALIZED":
            continue
        if row.target_valid:
            valid_declared += 1
            wrong = gt.visibility == 0 or math.hypot(row.x - gt.x, row.y - gt.y) > threshold_px
            false_valid += wrong
        if gt.visibility == 0:
            continue
        evaluable = row.target_valid or math.isfinite(row.x)
        err = math.hypot(row.x - gt.x, row.y - gt.y) if evaluable else math.nan
        errors.append(err)
        successes.append(row.target_valid and err <= threshold_px)
    finite = np.array([e for e in errors if math.isfinite(e)])
    return {
        "n_scored_visible": len(errors),
        "n_without_position": len(errors) - len(finite),
        "mean_position_error_px": float(finite.mean()) if finite.size else math.nan,
        "p95_position_error_px": float(np.percentile(finite, 95)) if finite.size else math.nan,
        "success_rate_at_20px": float(np.mean(successes)) if successes else math.nan,
        "false_valid_rate": false_valid / valid_declared if valid_declared else math.nan,
        "valid_declarations": valid_declared,
    }
