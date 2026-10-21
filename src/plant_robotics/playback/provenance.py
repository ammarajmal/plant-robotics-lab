"""Grounded manifest construction and deterministic content hashing."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from plant_robotics import __version__
from plant_robotics.playback.config import PlaybackConfig


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def config_checksum(config: PlaybackConfig) -> str:
    return hashlib.sha256(config.config_path.read_bytes()).hexdigest()


def path_reference(path: Path, *, base: Path) -> str:
    """Use portable config-relative references, or explicit absolute paths."""

    try:
        return f"config-relative:{path.relative_to(base).as_posix()}"
    except ValueError:
        return f"absolute:{path}"


def _git(config_path: Path) -> tuple[str | None, bool | None]:
    try:
        revision = subprocess.run(
            ["git", "-C", str(config_path.parent), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "-C", str(config_path.parent), "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        return revision, dirty
    except (OSError, subprocess.CalledProcessError):
        return None, None


def make_manifest(
    config: PlaybackConfig,
    *,
    status: str,
    errors: list[str],
    streams: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
) -> dict[str, Any]:
    revision, dirty = _git(config.config_path)
    return {
        "schema_version": 1,
        "created_utc": datetime.now(UTC).isoformat(),
        "run_id": config.run_id,
        "git": {"revision": revision, "dirty": dirty},
        "prl_version": __version__,
        "runtime": {
            "python": platform.python_version(),
            "opencv": cv2.__version__,
            "numpy": np.__version__,
        },
        "dataset": {"dataset_id": config.dataset_id, "episode_id": config.episode_id},
        "streams": streams,
        "alignment": {
            "timestamp_source": "nominal frame index divided by decoder-reported FPS",
            "method": "frame-index pairing in left_arm, middle, right_arm order",
            "exposure_synchronization": "unverified",
        },
        "configuration": {
            "path": path_reference(config.config_path, base=config.config_path.parent),
            "sha256": config_checksum(config),
        },
        "outputs": outputs,
        "execution": {"status": status, "errors": errors},
    }


def deterministic_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Remove explicitly volatile fields for repeatability comparisons."""

    result = json.loads(json.dumps(manifest))
    result.pop("created_utc", None)
    result.pop("run_id", None)
    result.get("git", {}).pop("dirty", None)
    result.get("execution", {}).pop("errors", None)
    return result
