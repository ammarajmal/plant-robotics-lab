"""Filesystem-independent records describing where an episode's media lives.

A manifest names streams by path *relative to a data root* that is supplied at
run time, so it stays portable across machines. These records hold no data
root and never open a file. They make no claim about camera exposure
synchronization; see ``alignment`` in :meth:`SourceManifest.to_dict`.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Final

from plant_robotics.domain.video import CameraId

SCHEMA_VERSION: Final = 1
CAMERA_ORDER: Final[tuple[CameraId, CameraId, CameraId]] = ("left_arm", "middle", "right_arm")
ALIGNMENT: Final = {
    "timestamp_provenance": "nominal_frame_index",
    "exposure_synchronization": "unverified",
}

_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_SHA256 = re.compile(r"[0-9a-f]{64}")


class ManifestError(ValueError):
    """A source manifest or one of its fields violates the contract."""


def validate_identifier(value: object, name: str) -> str:
    """Accept a single path-safe token (no separators, no leading dot or dash)."""

    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise ManifestError(f"{name} must match {_IDENTIFIER.pattern!r}, got {value!r}")
    return value


def validate_relative_path(value: object) -> str:
    """Accept only normalized, relative, forward-slash paths without ``..``."""

    if not isinstance(value, str) or not value or "\\" in value:
        raise ManifestError(f"relative_path must be a non-empty POSIX path, got {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts or str(path) != value:
        raise ManifestError(f"relative_path must be normalized and relative, got {value!r}")
    return value


def _positive_int(value: object, name: str, *, allow_zero: bool = False) -> int:
    floor = 0 if allow_zero else 1
    if isinstance(value, bool) or not isinstance(value, int) or value < floor:
        raise ManifestError(f"{name} must be an integer >= {floor}, got {value!r}")
    return value


def _check_keys(raw: Mapping[str, Any], expected: set[str], what: str) -> None:
    if not isinstance(raw, Mapping):
        raise ManifestError(f"{what} must be a mapping, got {type(raw).__name__}")
    missing = expected - raw.keys()
    if missing:
        raise ManifestError(f"{what} is missing keys: {sorted(missing)}")
    extra = raw.keys() - expected
    if extra:
        raise ManifestError(f"{what} has unexpected keys: {sorted(extra)}")


@dataclass(frozen=True, slots=True)
class StreamRecord:
    """Observed facts about one video file under the data root.

    ``sha256`` is ``None`` when hashing was skipped; that means "unverified",
    never "unchanged".
    """

    camera_id: CameraId
    relative_path: str
    size_bytes: int
    sha256: str | None
    width: int
    height: int
    fps: float
    frame_count: int
    codec: str
    backend: str

    _KEYS = (
        "camera_id relative_path size_bytes sha256 width height fps frame_count codec backend"
    ).split()

    def __post_init__(self) -> None:
        if self.camera_id not in CAMERA_ORDER:
            raise ManifestError(f"camera_id must be one of {CAMERA_ORDER}, got {self.camera_id!r}")
        validate_relative_path(self.relative_path)
        _positive_int(self.size_bytes, "size_bytes", allow_zero=True)
        if self.sha256 is not None and (
            not isinstance(self.sha256, str) or _SHA256.fullmatch(self.sha256) is None
        ):
            raise ManifestError(f"sha256 must be 64 lowercase hex digits or None: {self.sha256!r}")
        _positive_int(self.width, "width")
        _positive_int(self.height, "height")
        _positive_int(self.frame_count, "frame_count")
        if (
            isinstance(self.fps, bool)
            or not isinstance(self.fps, int | float)
            or not math.isfinite(self.fps)
            or self.fps <= 0
        ):
            raise ManifestError(f"fps must be positive and finite, got {self.fps!r}")
        if not isinstance(self.codec, str) or not isinstance(self.backend, str):
            raise ManifestError("codec and backend must be strings")

    def to_dict(self) -> dict[str, Any]:
        return {key: getattr(self, key) for key in self._KEYS}

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> StreamRecord:
        _check_keys(raw, set(cls._KEYS), "stream")
        return cls(**{key: raw[key] for key in cls._KEYS})


@dataclass(frozen=True, slots=True)
class SourceManifest:
    """Portable description of one three-view episode; media is referenced, not copied."""

    dataset_id: str
    task_id: str
    episode_id: str
    root_variable: str
    streams: tuple[StreamRecord, StreamRecord, StreamRecord]

    _KEYS = ("schema_version", "dataset_id", "task_id", "episode_id", "root_variable")

    def __post_init__(self) -> None:
        validate_identifier(self.dataset_id, "dataset_id")
        validate_identifier(self.task_id, "task_id")
        validate_identifier(self.episode_id, "episode_id")
        validate_identifier(self.root_variable, "root_variable")
        if len(self.streams) != 3:
            raise ManifestError(f"exactly three streams are required, got {len(self.streams)}")
        actual = tuple(stream.camera_id for stream in self.streams)
        if actual != CAMERA_ORDER:
            raise ManifestError(f"streams must be ordered {CAMERA_ORDER}, got {actual}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "dataset_id": self.dataset_id,
            "task_id": self.task_id,
            "episode_id": self.episode_id,
            "root_variable": self.root_variable,
            "alignment": dict(ALIGNMENT),
            "streams": [stream.to_dict() for stream in self.streams],
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> SourceManifest:
        _check_keys(raw, {*cls._KEYS, "alignment", "streams"}, "manifest")
        if raw["schema_version"] != SCHEMA_VERSION:
            raise ManifestError(f"schema_version must be {SCHEMA_VERSION}")
        if raw["alignment"] != ALIGNMENT:
            raise ManifestError(f"alignment must equal {ALIGNMENT}")
        if not isinstance(raw["streams"], list):
            raise ManifestError("streams must be a list")
        streams = tuple(StreamRecord.from_dict(item) for item in raw["streams"])
        return cls(
            dataset_id=raw["dataset_id"],
            task_id=raw["task_id"],
            episode_id=raw["episode_id"],
            root_variable=raw["root_variable"],
            streams=streams,  # type: ignore[arg-type]
        )
