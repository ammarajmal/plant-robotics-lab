from __future__ import annotations

import hashlib
import math
from pathlib import Path

import cv2
import numpy as np
import pytest

from plant_robotics.domain.video import (
    SynchronizationStatus,
    TimestampProvenance,
    ViewSpec,
)
from plant_robotics.io.video import (
    FrameDecodeError,
    ThreeViewAlignmentError,
    VideoIngestionError,
    inspect_video,
    iter_three_view,
    read_frame,
)


def write_video(path: Path, *, frames: int, fps: float = 10.0) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (64, 48))
    assert writer.isOpened()
    try:
        for index in range(frames):
            frame = np.full((48, 64, 3), index % 256, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()


def specs_for(tmp_path: Path, *, frame_counts: tuple[int, int, int] = (4, 4, 4)) -> list[ViewSpec]:
    specs = []
    for camera_id, frame_count in zip(
        ("left_arm", "middle", "right_arm"), frame_counts, strict=True
    ):
        path = tmp_path / f"{camera_id}.mp4"
        write_video(path, frames=frame_count)
        specs.append(ViewSpec(camera_id=camera_id, source=path))
    return specs


def test_inspect_video_reads_valid_metadata(tmp_path: Path) -> None:
    path = tmp_path / "clip.mp4"
    write_video(path, frames=4, fps=10.0)

    info = inspect_video(path, "left_arm")

    assert (info.width, info.height, info.fps, info.frame_count) == (64, 48, 10.0, 4)
    assert math.isclose(info.nominal_duration_s, 0.4)


def test_inspect_video_rejects_missing_and_corrupt_files(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="camera_id"):
        inspect_video(tmp_path / "missing.mp4", "not_a_camera")

    with pytest.raises(FileNotFoundError):
        inspect_video(tmp_path / "missing.mp4", "left_arm")

    corrupt = tmp_path / "corrupt.mp4"
    corrupt.write_text("not a video")
    with pytest.raises(VideoIngestionError):
        inspect_video(corrupt, "left_arm")


def test_read_frame_rejects_negative_and_out_of_range_indices(tmp_path: Path) -> None:
    path = tmp_path / "clip.mp4"
    write_video(path, frames=3)

    with pytest.raises(ValueError):
        read_frame(path, -1)
    with pytest.raises(FrameDecodeError):
        read_frame(path, 3)


def test_read_frame_is_repeatable_and_has_expected_shape_dtype(tmp_path: Path) -> None:
    path = tmp_path / "clip.mp4"
    write_video(path, frames=4)

    first = read_frame(path, 2)
    second = read_frame(path, 2)

    assert first.shape == second.shape == (48, 64, 3)
    assert first.dtype == second.dtype == np.uint8
    assert hashlib.sha256(first.tobytes()).digest() == hashlib.sha256(second.tobytes()).digest()
    assert math.isclose(float(first.mean()), 2.0, abs_tol=5.0)


def test_read_frame_releases_capture_on_decode_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "clip.mp4"
    write_video(path, frames=1)
    released = False
    real_release = cv2.VideoCapture.release

    def release(capture: cv2.VideoCapture) -> None:
        nonlocal released
        released = True
        real_release(capture)

    monkeypatch.setattr(cv2.VideoCapture, "release", release)
    with pytest.raises(FrameDecodeError):
        read_frame(path, 1)
    assert released


def test_iter_three_view_orders_views_and_preserves_provenance(tmp_path: Path) -> None:
    packets = list(iter_three_view(specs_for(tmp_path), stop_frame=2))

    assert [packet.frame_index for packet in packets] == [0, 1]
    assert [view.camera_id for view in packets[0].views] == ["left_arm", "middle", "right_arm"]
    assert packets[1].views[0].timing.frame_index == 1
    assert packets[1].views[0].timing.nominal_time_s == 0.1
    assert packets[1].timing_provenance is TimestampProvenance.NOMINAL_FRAME_INDEX
    assert packets[0].synchronization_status is SynchronizationStatus.NOMINAL_FRAME_INDEX_ONLY


def test_iter_three_view_rejects_unequal_counts_without_truncating(tmp_path: Path) -> None:
    with pytest.raises(ThreeViewAlignmentError, match="unequal frame counts"):
        list(iter_three_view(specs_for(tmp_path, frame_counts=(4, 3, 4))))


def test_iter_three_view_rejects_wrong_order_and_releases_on_consumer_stop(tmp_path: Path) -> None:
    specs = specs_for(tmp_path)
    with pytest.raises(ThreeViewAlignmentError, match="ordered"):
        list(iter_three_view([specs[1], specs[0], specs[2]]))

    iterator = iter_three_view(specs)
    next(iterator)
    iterator.close()
