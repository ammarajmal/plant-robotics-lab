from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from plant_robotics.io.video import inspect_video
from plant_robotics.playback.config import ConfigError, load_config
from plant_robotics.playback.provenance import deterministic_manifest, sha256_file
from plant_robotics.playback.render import PlaybackError, render_three_view


def _video(path: Path, count: int = 4, size: tuple[int, int] = (32, 24)) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, size)
    assert writer.isOpened()
    try:
        for index in range(count):
            writer.write(np.full((size[1], size[0], 3), index, dtype=np.uint8))
    finally:
        writer.release()


def _config(tmp_path: Path, counts: tuple[int, int, int] = (4, 4, 4)) -> Path:
    sources = []
    for camera, count in zip(("left_arm", "middle", "right_arm"), counts, strict=True):
        path = tmp_path / f"{camera}.mp4"
        _video(path, count)
        sources.append((camera, path.name))
    path = tmp_path / "config.yaml"
    lines = [
        "schema_version: 1",
        "dataset_id: synthetic",
        "episode_id: episode_00000",
        "run_id: test-run",
        "output_dir: output",
        "views:",
    ]
    for camera, source in sources:
        lines.extend([f"  - camera_id: {camera}", f"    source: {source}"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_manifest_has_grounded_hashes_labels_and_dimensions(tmp_path: Path) -> None:
    config = load_config(_config(tmp_path))
    manifest = render_three_view(config)

    assert [item["camera_id"] for item in manifest["streams"]] == [
        "left_arm",
        "middle",
        "right_arm",
    ]
    assert all(len(item["source_sha256"]) == 64 for item in manifest["streams"])
    assert (
        manifest["configuration"]["sha256"]
        == hashlib.sha256(config.config_path.read_bytes()).hexdigest()
    )
    assert manifest["alignment"]["exposure_synchronization"] == "unverified"
    assert [(item["width"], item["height"]) for item in manifest["streams"]] == [(32, 24)] * 3
    assert (config.resolved_output_dir / "contact_sheet.jpg").is_file()
    output_info = inspect_video(config.resolved_output_dir / "three_view.mp4", "left_arm")
    assert (output_info.width, output_info.height, output_info.frame_count) == (96, 24, 4)


def test_repeat_runs_have_deterministic_content_evidence(tmp_path: Path) -> None:
    config = load_config(_config(tmp_path))
    first = render_three_view(config)
    first_mp4_hash = sha256_file(config.resolved_output_dir / "three_view.mp4")
    second = render_three_view(config)
    assert deterministic_manifest(first) == deterministic_manifest(second)
    assert first_mp4_hash == sha256_file(config.resolved_output_dir / "three_view.mp4")


def test_config_rejects_wrong_order_before_processing(tmp_path: Path) -> None:
    path = _config(tmp_path)
    path.write_text(
        path.read_text().replace("camera_id: left_arm", "camera_id: middle", 1), encoding="utf-8"
    )
    with pytest.raises(ConfigError, match="ordered"):
        load_config(path)


def test_missing_input_and_mismatched_counts_report_failed_manifest(tmp_path: Path) -> None:
    path = _config(tmp_path, counts=(4, 3, 4))
    with pytest.raises(PlaybackError, match="unequal frame counts"):
        render_three_view(load_config(path))
    manifest = json.loads((tmp_path / "output" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["execution"]["status"] == "failed"


def test_writer_initialization_failure_reports_failure_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = load_config(_config(tmp_path))

    class ClosedWriter:
        def isOpened(self) -> bool:
            return False

        def release(self) -> None:
            pass

    monkeypatch.setattr(cv2, "VideoWriter", lambda *args: ClosedWriter())
    with pytest.raises(PlaybackError, match="initialize output writer"):
        render_three_view(config)
    manifest = json.loads(
        (config.resolved_output_dir / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["execution"]["status"] == "failed"


def test_cli_success_and_missing_config_failure(tmp_path: Path) -> None:
    config = _config(tmp_path)
    env = {**os.environ, "PYTHONPATH": "src"}
    success = subprocess.run(
        [
            sys.executable,
            "-m",
            "plant_robotics.cli",
            "playback",
            "three-view",
            "--config",
            str(config),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert success.returncode == 0
    assert "playback complete" in success.stdout
    failure = subprocess.run(
        [
            sys.executable,
            "-m",
            "plant_robotics.cli",
            "playback",
            "three-view",
            "--config",
            str(tmp_path / "missing.yaml"),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert failure.returncode == 2
    assert str(tmp_path / "missing.yaml") in failure.stderr
