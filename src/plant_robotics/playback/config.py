"""Validated YAML configuration for headless playback."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from plant_robotics.domain.video import CameraId, ViewSpec

CAMERAS: tuple[CameraId, ...] = ("left_arm", "middle", "right_arm")


class ConfigError(ValueError):
    """A playback configuration violates the media contract."""


@dataclass(frozen=True, slots=True)
class PlaybackConfig:
    config_path: Path
    dataset_id: str
    episode_id: str
    run_id: str
    views: tuple[ViewSpec, ViewSpec, ViewSpec]
    output_dir: Path
    codec: str = "mp4v"
    fps: float | None = None
    start_frame: int = 0
    stop_frame: int | None = None

    @property
    def resolved_output_dir(self) -> Path:
        return (
            self.output_dir
            if self.output_dir.is_absolute()
            else self.config_path.parent / self.output_dir
        )


def _required(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{key!r} must be a non-empty string")
    return value


def load_config(path: Path) -> PlaybackConfig:
    """Load and validate configuration before opening any source or writer."""

    config_path = Path(path).resolve()
    if not config_path.is_file():
        raise FileNotFoundError(config_path)
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML: {config_path}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("configuration root must be a mapping")
    if raw.get("schema_version") not in (None, 1):
        raise ConfigError("schema_version must be 1")
    dataset_id = _required(raw, "dataset_id")
    episode_id = _required(raw, "episode_id")
    run_id = _required(raw, "run_id")
    output_dir = Path(_required(raw, "output_dir"))
    output = raw.get("output", {})
    if not isinstance(output, dict):
        raise ConfigError("output must be a mapping")
    codec = output.get("codec", "mp4v")
    if not isinstance(codec, str) or len(codec) != 4:
        raise ConfigError("output.codec must be a four-character string")
    fps = output.get("fps")
    if fps is not None and (isinstance(fps, bool) or not isinstance(fps, (int, float)) or fps <= 0):
        raise ConfigError("output.fps must be positive when supplied")
    start_frame = raw.get("start_frame", 0)
    stop_frame = raw.get("stop_frame")
    if not isinstance(start_frame, int) or isinstance(start_frame, bool) or start_frame < 0:
        raise ConfigError("start_frame must be a non-negative integer")
    if stop_frame is not None and (
        not isinstance(stop_frame, int) or isinstance(stop_frame, bool) or stop_frame <= start_frame
    ):
        raise ConfigError("stop_frame must be an integer greater than start_frame")
    raw_views = raw.get("views")
    if not isinstance(raw_views, list) or len(raw_views) != 3:
        raise ConfigError("views must contain exactly three entries")
    views: list[ViewSpec] = []
    for expected, item in zip(CAMERAS, raw_views, strict=True):
        if not isinstance(item, dict) or item.get("camera_id") != expected:
            raise ConfigError(f"views must be ordered {CAMERAS}")
        source = item.get("source")
        if not isinstance(source, str) or not source.strip():
            raise ConfigError(f"{expected}.source must be a non-empty path")
        source_path = Path(source)
        if not source_path.is_absolute():
            source_path = config_path.parent / source_path
        views.append(ViewSpec(expected, source_path.resolve()))
    return PlaybackConfig(
        config_path=config_path,
        dataset_id=dataset_id,
        episode_id=episode_id,
        run_id=run_id,
        views=tuple(views),  # type: ignore[arg-type]
        output_dir=output_dir,
        codec=codec,
        fps=float(fps) if fps is not None else None,
        start_frame=start_frame,
        stop_frame=stop_frame,
    )
