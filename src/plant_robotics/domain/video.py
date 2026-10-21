"""Hardware-independent contracts for deterministic video playback.

These records describe decoded media and nominal playback position. They do
not claim physical camera exposure timestamps or cross-camera synchronization.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal

import numpy as np

CameraId = Literal["left_arm", "middle", "right_arm"]


class TimestampProvenance(StrEnum):
    """How a playback time was obtained."""

    NOMINAL_FRAME_INDEX = "nominal_frame_index"


class SynchronizationStatus(StrEnum):
    """Evidence level for a multi-view packet.

    Only the conservative state is currently representable. A verified state
    must not be added until a separate evidence-backed validation mechanism
    exists.
    """

    NOMINAL_FRAME_INDEX_ONLY = "nominal_frame_index_only"


@dataclass(frozen=True, slots=True)
class FrameTiming:
    """Playback timing derived from a stream's reported FPS."""

    frame_index: int
    nominal_time_s: float
    provenance: TimestampProvenance = TimestampProvenance.NOMINAL_FRAME_INDEX


@dataclass(frozen=True, slots=True)
class VideoStreamInfo:
    """Container/decoder metadata for one video stream."""

    source_path: Path
    camera_id: CameraId
    width: int
    height: int
    fps: float
    frame_count: int
    backend: str = "unknown"
    codec: str = "unknown"

    @property
    def nominal_duration_s(self) -> float:
        """Return ``frame_count / fps``; this is not measured exposure time."""

        return self.frame_count / self.fps


@dataclass(frozen=True, slots=True)
class FramePacket:
    """One decoded frame and its explicit playback provenance."""

    camera_id: CameraId
    timing: FrameTiming
    frame: np.ndarray
    stream_info: VideoStreamInfo


@dataclass(frozen=True, slots=True)
class ViewSpec:
    """A named camera stream selected for multi-view playback."""

    camera_id: CameraId
    source: Path


@dataclass(frozen=True, slots=True)
class ThreeViewPacket:
    """Three nominally frame-index-paired views.

    The view order is always left arm, middle, right arm. Equal frame indices
    and FPS are structural playback facts, not physical synchronization.
    """

    frame_index: int
    views: tuple[FramePacket, FramePacket, FramePacket]
    synchronization_status: SynchronizationStatus = SynchronizationStatus.NOMINAL_FRAME_INDEX_ONLY

    @property
    def timing_provenance(self) -> TimestampProvenance:
        return self.views[0].timing.provenance
