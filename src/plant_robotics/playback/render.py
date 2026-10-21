"""Sequential three-view MP4 and contact-sheet rendering."""

from __future__ import annotations

import json
from itertools import chain
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from plant_robotics.io.video import iter_three_view
from plant_robotics.playback.config import PlaybackConfig
from plant_robotics.playback.provenance import make_manifest, path_reference, sha256_file


class PlaybackError(RuntimeError):
    """Playback failed after configuration validation."""


def _annotate(frame: np.ndarray, camera_id: str, frame_index: int) -> np.ndarray:
    image = frame.copy()
    cv2.rectangle(image, (0, 0), (image.shape[1], 42), (0, 0, 0), -1)
    cv2.putText(
        image,
        f"{camera_id}  source frame {frame_index}",
        (8, 17),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        image,
        "ALIGNMENT NOMINAL ONLY",
        (8, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.38,
        (0, 220, 255),
        1,
        cv2.LINE_AA,
    )
    return image


def _write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_three_view(config: PlaybackConfig) -> dict[str, Any]:
    """Render sequentially and always leave a success or failure manifest."""

    output_dir = config.resolved_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    output_path = output_dir / "three_view.mp4"
    sheet_path = output_dir / "contact_sheet.jpg"
    errors: list[str] = []
    streams: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
    writer: cv2.VideoWriter | None = None
    status = "failed"
    try:
        iterator = iter_three_view(
            config.views, start_frame=config.start_frame, stop_frame=config.stop_frame
        )
        first = next(iterator, None)
        if first is None:
            raise PlaybackError("selected frame range is empty")
        infos = [view.stream_info for view in first.views]
        fps = config.fps or infos[0].fps
        size = (sum(info.width for info in infos), infos[0].height)
        writer = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*config.codec), fps, size)
        if not writer.isOpened():
            raise PlaybackError(f"could not initialize output writer: {output_path}")
        for info in infos:
            streams.append(
                {
                    "camera_id": info.camera_id,
                    "source": path_reference(
                        info.source_path, base=config.config_path.parent, data_root=config.data_root
                    ),
                    "source_sha256": sha256_file(info.source_path),
                    "width": info.width,
                    "height": info.height,
                    "fps": info.fps,
                    "frame_count": info.frame_count,
                    "backend": info.backend,
                    "codec": info.codec,
                }
            )
        samples: list[np.ndarray] = []
        for packet in chain((first,), iterator):
            combined = cv2.hconcat(
                [_annotate(view.frame, view.camera_id, packet.frame_index) for view in packet.views]
            )
            writer.write(combined)
            if len(samples) < 6 and (
                packet.frame_index == config.start_frame
                or packet.frame_index % max(1, infos[0].frame_count // 5) == 0
            ):
                samples.append(combined.copy())
        writer.release()
        writer = None
        if not samples:
            raise PlaybackError("no frames available for contact sheet")
        cols = min(2, len(samples))
        rows = (len(samples) + cols - 1) // cols
        sheet = np.zeros((rows * size[1], cols * size[0], 3), dtype=np.uint8)
        for index, sample in enumerate(samples):
            row, col = divmod(index, cols)
            sheet[row * size[1] : (row + 1) * size[1], col * size[0] : (col + 1) * size[0]] = sample
        if not cv2.imwrite(str(sheet_path), sheet):
            raise PlaybackError(f"could not write contact sheet: {sheet_path}")
        outputs = [
            {
                "kind": "playback_mp4",
                "path": path_reference(
                    output_path, base=config.config_path.parent, allow_parents=True
                ),
                "sha256": sha256_file(output_path),
            },
            {
                "kind": "contact_sheet",
                "path": path_reference(
                    sheet_path, base=config.config_path.parent, allow_parents=True
                ),
                "sha256": sha256_file(sheet_path),
            },
        ]
        status = "success"
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
    finally:
        if writer is not None:
            writer.release()
        _write_manifest(
            manifest_path,
            make_manifest(config, status=status, errors=errors, streams=streams, outputs=outputs),
        )
    if status != "success":
        raise PlaybackError(errors[-1])
    return json.loads(manifest_path.read_text(encoding="utf-8"))
