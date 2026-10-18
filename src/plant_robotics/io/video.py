"""OpenCV-backed deterministic video ingestion.

This module owns media I/O only. It does not render frames, detect targets,
track identities, or infer physical synchronization.
"""

from __future__ import annotations

import math
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Final

import cv2
import numpy as np

from plant_robotics.domain.video import (
    CameraId,
    FramePacket,
    FrameTiming,
    ThreeViewPacket,
    TimestampProvenance,
    VideoStreamInfo,
    ViewSpec,
)

VALID_CAMERA_IDS: Final[tuple[CameraId, CameraId, CameraId]] = (
    "left_arm",
    "middle",
    "right_arm",
)


class VideoIngestionError(ValueError):
    """Base class for an existing file that cannot satisfy the media contract."""


class FrameDecodeError(VideoIngestionError):
    """A requested frame could not be decoded."""


class ThreeViewAlignmentError(VideoIngestionError):
    """The selected streams cannot be paired without silent substitution."""


def _validate_camera_id(camera_id: str) -> CameraId:
    if camera_id not in VALID_CAMERA_IDS:
        raise ValueError(f"camera_id must be one of {VALID_CAMERA_IDS}, got {camera_id!r}")
    return camera_id  # type: ignore[return-value]


def _open_capture(path: Path) -> cv2.VideoCapture:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(path)
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        capture.release()
        raise VideoIngestionError(f"could not open video for decoding: {path}")
    return capture


def inspect_video(path: Path, camera_id: str) -> VideoStreamInfo:
    """Inspect and validate decoder-reported metadata without reading frames."""

    valid_camera = _validate_camera_id(camera_id)
    path = Path(path)
    capture = _open_capture(path)
    try:
        width = capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        fps = capture.get(cv2.CAP_PROP_FPS)
        frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        for name, value in (("width", width), ("height", height), ("frame_count", frame_count)):
            if not math.isfinite(value) or value <= 0 or not value.is_integer():
                raise VideoIngestionError(f"{name} must be a positive integer, got {value!r}")
        if not math.isfinite(fps) or fps <= 0:
            raise VideoIngestionError(f"fps must be positive and finite, got {fps!r}")
        return VideoStreamInfo(
            source_path=path,
            camera_id=valid_camera,
            width=int(width),
            height=int(height),
            fps=float(fps),
            frame_count=int(frame_count),
        )
    finally:
        capture.release()


def read_frame(path: Path, frame_index: int) -> np.ndarray:
    """Decode one zero-based frame by sequentially reading from the stream start."""

    if frame_index < 0:
        raise ValueError(f"frame_index must be non-negative, got {frame_index!r}")
    capture = _open_capture(Path(path))
    try:
        for decoded_count in range(frame_index + 1):
            ok, frame = capture.read()
            if not ok or frame is None:
                raise FrameDecodeError(
                    f"could not decode frame {frame_index}; stream ended after "
                    f"{decoded_count} frames: {path}"
                )
        return frame
    finally:
        capture.release()


def _validate_view_specs(view_specs: Sequence[ViewSpec]) -> tuple[ViewSpec, ViewSpec, ViewSpec]:
    if len(view_specs) != 3:
        raise ThreeViewAlignmentError(f"exactly three views are required, got {len(view_specs)}")
    expected = tuple(VALID_CAMERA_IDS)
    actual = tuple(spec.camera_id for spec in view_specs)
    if actual != expected:
        raise ThreeViewAlignmentError(f"views must be ordered {expected}, got {actual}")
    return view_specs[0], view_specs[1], view_specs[2]


def iter_three_view(
    view_specs: Sequence[ViewSpec],
    *,
    start_frame: int = 0,
    stop_frame: int | None = None,
) -> Iterator[ThreeViewPacket]:
    """Yield nominal frame-index pairs for exactly three equal-length streams.

    Streams are inspected before any frame is yielded. Unequal frame counts,
    dimensions, or FPS values fail rather than truncating, duplicating, or
    silently substituting frames.
    """

    if start_frame < 0:
        raise ValueError(f"start_frame must be non-negative, got {start_frame!r}")
    specs = _validate_view_specs(view_specs)
    infos = tuple(inspect_video(spec.source, spec.camera_id) for spec in specs)
    if len({info.frame_count for info in infos}) != 1:
        raise ThreeViewAlignmentError("three-view streams have unequal frame counts")
    if len({(info.width, info.height) for info in infos}) != 1:
        raise ThreeViewAlignmentError("three-view streams have unequal dimensions")
    if len({info.fps for info in infos}) != 1:
        raise ThreeViewAlignmentError("three-view streams have unequal reported FPS")
    end_frame = infos[0].frame_count if stop_frame is None else stop_frame
    if end_frame < start_frame or end_frame > infos[0].frame_count:
        raise ValueError(
            f"stop_frame must be in [{start_frame}, {infos[0].frame_count}], got {end_frame}"
        )
    captures = tuple(_open_capture(spec.source) for spec in specs)
    try:
        for skipped_index in range(start_frame):
            for capture, info in zip(captures, infos, strict=True):
                ok, _ = capture.read()
                if not ok:
                    raise FrameDecodeError(
                        f"could not decode frame {skipped_index} while reaching "
                        f"start_frame {start_frame} for {info.camera_id}: {info.source_path}"
                    )
        for frame_index in range(start_frame, end_frame):
            packets: list[FramePacket] = []
            for capture, info in zip(captures, infos, strict=True):
                ok, frame = capture.read()
                if not ok or frame is None:
                    raise FrameDecodeError(
                        f"could not decode frame {frame_index} for {info.camera_id}: "
                        f"{info.source_path}"
                    )
                packets.append(
                    FramePacket(
                        camera_id=info.camera_id,
                        timing=FrameTiming(
                            frame_index=frame_index,
                            nominal_time_s=frame_index / info.fps,
                            provenance=TimestampProvenance.NOMINAL_FRAME_INDEX,
                        ),
                        frame=frame,
                        stream_info=info,
                    )
                )
            yield ThreeViewPacket(frame_index=frame_index, views=tuple(packets))  # type: ignore[arg-type]
    finally:
        for capture in captures:
            capture.release()
