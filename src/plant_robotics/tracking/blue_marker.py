"""Classical blue-marker baselines: B0 (HSV detection) and B1 (HSV + Kalman).

A clean-room port for PRL-007 of the behaviour described in NORMAN's
``norman_blue_tracker.py`` / ``track_video.py``; the OpenCV Kalman filter is
kept so results are comparable. Image-plane only: no calibration, no
synchronization and no 3D claim. A ``VISIBLE`` row means "a blue blob was
associated", not that the physical target is verified.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np

Baseline = Literal["b0", "b1"]


@dataclass(frozen=True)
class TrackerConfig:
    hsv_lower: tuple[int, int, int] = (95, 55, 12)
    hsv_upper: tuple[int, int, int] = (145, 255, 255)
    morph_open: int = 3
    morph_close: int = 5
    min_area_px: int = 8
    max_area_px: int = 3500
    max_distance_px: float = 85.0
    area_change_weight: float = 12.0
    process_noise: float = 1.0
    measurement_noise: float = 12.0
    initial_covariance: float = 100.0
    partial_after_misses: int = 1
    predicted_after_misses: int = 3
    lost_after_misses: int = 15

    def __post_init__(self) -> None:
        for name in ("process_noise", "measurement_noise", "initial_covariance", "max_distance_px"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a positive finite number, got {value}")
        if (
            not 0
            <= self.partial_after_misses
            <= self.predicted_after_misses
            <= self.lost_after_misses
        ):
            raise ValueError("miss thresholds must satisfy partial <= predicted <= lost")
        if not 0 <= self.min_area_px <= self.max_area_px:
            raise ValueError("area bounds must satisfy 0 <= min <= max")


@dataclass(frozen=True)
class Candidate:
    x: float
    y: float
    w: int
    h: int
    area: int


@dataclass(frozen=True)
class TrackRow:
    frame: int
    x: float
    y: float
    state: str
    source: str
    target_valid: bool


_NAN = float("nan")


def detect(frame: np.ndarray, cfg: TrackerConfig) -> list[Candidate]:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(cfg.hsv_lower, np.uint8), np.array(cfg.hsv_upper, np.uint8))
    if cfg.morph_open > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (cfg.morph_open,) * 2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    if cfg.morph_close > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (cfg.morph_close,) * 2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    count, _, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    found = []
    for i in range(1, count):
        x, y, w, h, area = (int(v) for v in stats[i])
        if cfg.min_area_px <= area <= cfg.max_area_px:
            found.append(Candidate(float(centroids[i][0]), float(centroids[i][1]), w, h, area))
    return found


def _kalman(fps: float, cfg: TrackerConfig) -> cv2.KalmanFilter:
    dt = 1.0 / fps
    kf = cv2.KalmanFilter(4, 2)
    kf.transitionMatrix = np.array(
        [[1, 0, dt, 0], [0, 1, 0, dt], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=np.float32
    )
    kf.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], dtype=np.float32)
    kf.processNoiseCov = np.eye(4, dtype=np.float32) * cfg.process_noise
    kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * cfg.measurement_noise
    kf.errorCovPost = np.eye(4, dtype=np.float32) * cfg.initial_covariance
    return kf


def run_baseline(
    frames: Iterable[tuple[int, np.ndarray]],
    baseline: Baseline,
    seed_frame: int,
    seed_xy: tuple[float, float],
    fps: float,
    cfg: TrackerConfig | None = None,
) -> list[TrackRow]:
    """Track one seeded target. Frames before ``seed_frame`` are UNINITIALIZED."""
    cfg = cfg or TrackerConfig()
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError(f"fps must be a positive finite number, got {fps}")
    if seed_frame < 0:
        raise ValueError(f"seed_frame must be non-negative, got {seed_frame}")
    kf = _kalman(fps, cfg) if baseline == "b1" else None
    last = seed_xy
    prev_area: float | None = None
    misses = 0
    rows: list[TrackRow] = []
    for index, frame in frames:
        if index < seed_frame:
            rows.append(TrackRow(index, _NAN, _NAN, "UNINITIALIZED", "none", False))
            continue
        candidates = detect(frame, cfg)
        if baseline == "b0":
            best = _nearest(candidates, last, cfg, None)
            if best is None:
                rows.append(TrackRow(index, _NAN, _NAN, "LOST", "none", False))
            else:
                last = (best.x, best.y)
                rows.append(TrackRow(index, best.x, best.y, "VISIBLE", "hsv", True))
            continue
        assert kf is not None
        if index == seed_frame:
            kf.statePost = np.array([[seed_xy[0]], [seed_xy[1]], [0], [0]], dtype=np.float32)
            kf.statePre = kf.statePost.copy()
        predicted = kf.predict()
        pred = (float(predicted[0, 0]), float(predicted[1, 0]))
        best = _nearest(candidates, pred, cfg, prev_area)
        if best is not None:
            corrected = kf.correct(np.array([[best.x], [best.y]], dtype=np.float32))
            prev_area, misses = float(best.area), 0
            rows.append(
                TrackRow(
                    index,
                    float(corrected[0, 0]),
                    float(corrected[1, 0]),
                    "VISIBLE",
                    "measurement",
                    True,
                )
            )
            continue
        misses += 1
        if misses >= cfg.lost_after_misses:
            rows.append(TrackRow(index, _NAN, _NAN, "LOST", "prediction", False))
        else:
            state = (
                "PREDICTED"
                if misses >= cfg.predicted_after_misses
                else "PARTIAL_OCCLUSION"
                if misses >= cfg.partial_after_misses
                else "VISIBLE"
            )
            rows.append(TrackRow(index, pred[0], pred[1], state, "prediction", False))
    return rows


def _nearest(
    candidates: list[Candidate],
    near: tuple[float, float],
    cfg: TrackerConfig,
    prev_area: float | None,
) -> Candidate | None:
    best, best_score = None, math.inf
    for c in candidates:
        dist = math.hypot(c.x - near[0], c.y - near[1])
        if dist >= cfg.max_distance_px:
            continue
        penalty = 0.0
        if prev_area:
            penalty = abs(math.log(max(c.area, 1) / prev_area))
        score = dist + cfg.area_change_weight * penalty
        if score < best_score:
            best, best_score = c, score
    return best
