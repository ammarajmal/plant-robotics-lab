"""Full sequential decode audit: what the decoder actually yields, frame by frame.

Container metadata (``CAP_PROP_FRAME_COUNT``) is a header claim. This module
decodes every frame, counts what succeeds, hashes the decoded pixels, and
records the decoder's reported presentation time (``CAP_PROP_POS_MSEC``) as
*decoder-reported evidence only*: it is not exposure time and says nothing about
camera synchronization. Files are opened read-only; nothing is written here.

Frame hashes cover decoded pixels, so they depend on the decoder build and are
a different object from the SHA-256 of the encoded MP4.
"""

from __future__ import annotations

import hashlib
import math
import platform
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import cv2
import numpy as np

from plant_robotics import __version__
from plant_robotics.domain.datasets import ALIGNMENT, CAMERA_ORDER, SourceManifest
from plant_robotics.io.resolver import Catalog, locate_stream, open_root, verify_episode
from plant_robotics.io.video import VideoIngestionError, inspect_video, open_capture

SCHEMA_VERSION: Final = 1
FRAME_HASH_SCHEMA: Final = "prl-frame-v1"


class SourceDriftError(ValueError):
    """Sources differ from the manifest, so decoding them would audit the wrong bytes."""

    def __init__(self, differences: tuple[str, ...]) -> None:
        super().__init__("; ".join(differences))
        self.differences = differences


def canonical_frame_digest(frame: np.ndarray) -> str:
    """SHA-256 over a self-describing header plus the C-contiguous pixel bytes.

    The header pins dtype, shape and channel order, so two arrays with equal
    bytes but different shapes or layouts cannot collide by accident.
    """

    array = np.ascontiguousarray(frame)
    header = f"{FRAME_HASH_SCHEMA}|{array.dtype.str}|{','.join(map(str, array.shape))}|BGR|C\n"
    digest = hashlib.sha256(header.encode("ascii"))
    digest.update(array)
    return digest.hexdigest()


def _chain(digests: list[str]) -> str:
    return hashlib.sha256("".join(f"{d}\n" for d in digests).encode("ascii")).hexdigest()


def _timing_summary(values: list[float]) -> dict[str, Any]:
    steps = [b - a for a, b in zip(values, values[1:], strict=False)]
    return {
        "first_ms": values[0] if values else None,
        "last_ms": values[-1] if values else None,
        "min_step_ms": min(steps) if steps else None,
        "max_step_ms": max(steps) if steps else None,
        "non_increasing_steps": sum(1 for step in steps if step <= 0),
        "non_finite_values": sum(1 for v in values if not math.isfinite(v)),
    }


def audit_stream(path: Path, camera_id: str) -> dict[str, Any]:
    """Decode one stream to the end and report what was observed, never raising on bad media."""

    record: dict[str, Any] = {"camera_id": camera_id}
    try:
        info = inspect_video(path, camera_id)
        capture = open_capture(path)
    except (VideoIngestionError, OSError) as exc:
        record.update(status="failed", anomalies=[f"cannot open: {exc}"])
        return record
    expected_shape = (info.height, info.width, 3)
    anomalies: list[str] = []
    digests: list[str] = []
    positions: list[float] = []
    try:
        while True:
            try:
                ok, frame = capture.read()
            except cv2.error as exc:
                anomalies.append(f"decoder exception at frame {len(digests)}: {exc}")
                break
            if not ok or frame is None:
                break
            index = len(digests)
            if frame.dtype != np.uint8 or frame.shape != expected_shape:
                anomalies.append(
                    f"frame {index}: {frame.dtype}{frame.shape}, expected uint8{expected_shape}"
                )
            digests.append(canonical_frame_digest(frame))
            positions.append(float(capture.get(cv2.CAP_PROP_POS_MSEC)))
    finally:
        capture.release()
    decoded = len(digests)
    matches = decoded == info.frame_count
    if not matches:
        anomalies.append(
            f"stream ended after {decoded} decoded frames; container metadata claims "
            f"{info.frame_count} (premature end of stream or a wrong header)"
        )
    record.update(
        status="complete" if matches and not anomalies else "incomplete",
        metadata={
            "width": info.width,
            "height": info.height,
            "fps": info.fps,
            "frame_count": info.frame_count,
            "codec": info.codec,
            "backend": info.backend,
        },
        decoded_frame_count=decoded,
        frame_count_matches_metadata=matches,
        frame_count_difference=decoded - info.frame_count,
        anomalies=anomalies,
        stream_digest=_chain(digests),
        frame_sha256=digests,
        decoder_pos_msec=positions,
        decoder_pos_msec_summary=_timing_summary(positions),
    )
    return record


def _build_info_versions() -> dict[str, str | None]:
    text = cv2.getBuildInformation()
    found: dict[str, str | None] = {}
    for key in ("avcodec", "avformat", "avutil"):
        match = re.search(rf"{key}:\s+YES \(([\d.]+)\)", text)
        found[key] = match.group(1) if match else None
    return found


def _git_state() -> dict[str, Any]:
    here = str(Path(__file__).resolve().parent)
    try:
        revision = subprocess.run(
            ["git", "-C", here, "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "-C", here, "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        return {"revision": revision, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"revision": None, "dirty": None}


def audit_episode(
    manifest: SourceManifest,
    data_root: Path,
    catalog: Catalog,
    *,
    manifest_sha256: str | None = None,
) -> dict[str, Any]:
    """Verify sources against the manifest and catalog, then decode all three streams."""

    verification = verify_episode(manifest, data_root, catalog=catalog)
    if not verification.ok:
        raise SourceDriftError(verification.differences)
    root = open_root(data_root)
    started = time.perf_counter()
    streams: list[dict[str, Any]] = []
    for recorded in manifest.streams:
        path = locate_stream(root, recorded.relative_path, recorded.camera_id)
        result = audit_stream(path, recorded.camera_id)
        result["relative_path"] = recorded.relative_path
        result["encoded_file_sha256"] = recorded.sha256
        streams.append(result)
    elapsed = time.perf_counter() - started
    counts = [s.get("decoded_frame_count") for s in streams]
    complete = all(s["status"] == "complete" for s in streams)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "full_decode_audit",
        "created_utc": datetime.now(UTC).isoformat(),
        "dataset": {
            "dataset_id": manifest.dataset_id,
            "task_id": manifest.task_id,
            "episode_id": manifest.episode_id,
            "root_variable": manifest.root_variable,
        },
        "source_manifest_sha256": manifest_sha256,
        "identity": "manifest paths equal the catalog layout; no symlink redirection",
        "alignment": {
            **ALIGNMENT,
            "decoder_pos_msec": "decoder-reported presentation time; not exposure time",
        },
        "frame_hash": {
            "schema": FRAME_HASH_SCHEMA,
            "covers": "dtype, shape, channel order (BGR), C-contiguous decoded pixel bytes",
            "scope": "decoded pixels under the recorded decoder build; not the encoded MP4 hash",
        },
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "opencv": cv2.__version__,
            "numpy": np.__version__,
            "ffmpeg_libraries": _build_info_versions(),
            "prl_version": __version__,
        },
        "git": _git_state(),
        "elapsed_s": elapsed,
        "streams": streams,
        "summary": {
            "cameras": list(CAMERA_ORDER),
            "all_streams_complete": complete,
            "decoded_counts": counts,
            "decoded_counts_equal": len(set(counts)) == 1,
            "episode_digest": _chain([s.get("stream_digest", "") for s in streams]),
        },
    }


def deterministic_audit(audit: dict[str, Any]) -> dict[str, Any]:
    """Drop volatile fields (clock, runtime duration, working-tree dirtiness)."""

    result = {k: v for k, v in audit.items() if k not in ("created_utc", "elapsed_s")}
    result["git"] = {"revision": audit["git"]["revision"]}
    return result
