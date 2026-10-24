from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

import plant_robotics.io.decode_audit as audit_module
from plant_robotics.cli import main
from plant_robotics.domain.video import VideoStreamInfo
from plant_robotics.io.decode_audit import (
    SourceDriftError,
    audit_episode,
    audit_stream,
    canonical_frame_digest,
    deterministic_audit,
)
from plant_robotics.io.resolver import Catalog, resolve_episode

CAMERAS = ("left_arm", "middle", "right_arm")
CATALOG = Catalog("synthetic", "PRL_DATA_ROOT", "ds/raw/{task_id}/{episode_id}/{camera_id}.mp4")


def _video(path: Path, count: int = 5) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (32, 24))
    assert writer.isOpened()
    for index in range(count):
        writer.write(np.full((24, 32, 3), index * 20, dtype=np.uint8))
    writer.release()


@pytest.fixture
def tree(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "root"
    folder = root / "ds/raw/task_a/episode_00000"
    folder.mkdir(parents=True)
    for camera in CAMERAS:
        _video(folder / f"{camera}.mp4")
    return root, folder


class FakeCapture:
    """A scripted decoder: yields ``frames`` then stops, optionally raising."""

    def __init__(self, frames: list[np.ndarray], raise_at: int | None = None) -> None:
        self.frames, self.raise_at, self.index = frames, raise_at, 0

    def read(self):
        if self.raise_at == self.index:
            raise cv2.error("scripted decoder failure")
        if self.index >= len(self.frames):
            return False, None
        frame = self.frames[self.index]
        self.index += 1
        return True, frame

    def get(self, _prop: int) -> float:
        return self.index * 100.0

    def release(self) -> None:
        pass


def _patch_decoder(monkeypatch: pytest.MonkeyPatch, capture: FakeCapture, declared: int) -> None:
    info = VideoStreamInfo(
        source_path=Path("x.mp4"), camera_id="middle", width=32, height=24, fps=10.0,
        frame_count=declared, backend="FAKE", codec="fake",
    )  # fmt: skip
    monkeypatch.setattr(audit_module, "inspect_video", lambda *_a: info)
    monkeypatch.setattr(audit_module, "open_capture", lambda _p: capture)


def _frames(n: int) -> list[np.ndarray]:
    return [np.full((24, 32, 3), i, dtype=np.uint8) for i in range(n)]


def test_frame_digest_binds_dtype_shape_and_bytes() -> None:
    base = np.arange(24, dtype=np.uint8).reshape(2, 4, 3)
    assert canonical_frame_digest(base) == canonical_frame_digest(base.copy())
    assert canonical_frame_digest(base) != canonical_frame_digest(base.reshape(4, 2, 3))
    assert canonical_frame_digest(base) != canonical_frame_digest(base.astype(np.int8))
    changed = base.copy()
    changed[0, 0, 0] ^= 1
    assert canonical_frame_digest(base) != canonical_frame_digest(changed)
    assert canonical_frame_digest(base) == canonical_frame_digest(np.asfortranarray(base))


def test_clean_stream_decodes_completely_and_counts_independently(tree) -> None:
    _, folder = tree
    record = audit_stream(folder / "middle.mp4", "middle")
    assert record["status"] == "complete"
    assert record["decoded_frame_count"] == record["metadata"]["frame_count"] == 5
    assert record["frame_count_matches_metadata"] and record["anomalies"] == []
    assert len(record["frame_sha256"]) == len(record["decoder_pos_msec"]) == 5


def test_header_overclaiming_frames_is_reported_as_premature_end(monkeypatch) -> None:
    _patch_decoder(monkeypatch, FakeCapture(_frames(4)), declared=7)
    record = audit_stream(Path("x.mp4"), "middle")
    assert record["status"] == "incomplete"
    assert record["decoded_frame_count"] == 4
    assert record["frame_count_difference"] == -3
    assert any("premature end" in a for a in record["anomalies"])


def test_header_underclaiming_frames_is_also_a_mismatch(monkeypatch) -> None:
    _patch_decoder(monkeypatch, FakeCapture(_frames(6)), declared=4)
    record = audit_stream(Path("x.mp4"), "middle")
    assert record["status"] == "incomplete" and record["frame_count_difference"] == 2


def test_mid_stream_decoder_exception_is_recorded_not_swallowed(monkeypatch) -> None:
    _patch_decoder(monkeypatch, FakeCapture(_frames(5), raise_at=2), declared=5)
    record = audit_stream(Path("x.mp4"), "middle")
    assert record["status"] == "incomplete" and record["decoded_frame_count"] == 2
    assert any("decoder exception at frame 2" in a for a in record["anomalies"])


def test_wrong_shape_or_dtype_frame_is_an_anomaly(monkeypatch) -> None:
    frames = _frames(3)
    frames[1] = np.zeros((24, 16, 3), dtype=np.uint8)
    frames[2] = np.zeros((24, 32, 3), dtype=np.uint16)
    _patch_decoder(monkeypatch, FakeCapture(frames), declared=3)
    record = audit_stream(Path("x.mp4"), "middle")
    assert record["status"] == "incomplete" and len(record["anomalies"]) == 2


def test_unreadable_media_is_a_failed_record_not_an_exception(tmp_path: Path) -> None:
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(b"not a video")
    assert audit_stream(bad, "middle")["status"] == "failed"
    assert audit_stream(tmp_path / "missing.mp4", "middle")["status"] == "failed"


def test_timing_summary_flags_non_increasing_steps() -> None:
    summary = audit_module._timing_summary([0.0, 100.0, 100.0, 90.0])
    assert summary["non_increasing_steps"] == 2 and summary["max_step_ms"] == 100.0


def test_episode_audit_is_deterministic_and_labels_limits(tree) -> None:
    root, _ = tree
    manifest = resolve_episode(CATALOG, root, "task_a", "episode_00000")
    first = audit_episode(manifest, root, CATALOG)
    second = audit_episode(manifest, root, CATALOG)
    assert deterministic_audit(first) == deterministic_audit(second)
    assert first["summary"]["all_streams_complete"] and first["summary"]["decoded_counts_equal"]
    assert first["alignment"]["exposure_synchronization"] == "unverified"
    assert "not exposure time" in first["alignment"]["decoder_pos_msec"]
    assert "not the encoded MP4 hash" in first["frame_hash"]["scope"]
    assert first["runtime"]["opencv"] == cv2.__version__
    assert [s["camera_id"] for s in first["streams"]] == list(CAMERAS)
    json.dumps(first, allow_nan=False)


def test_audit_refuses_when_sources_drifted_from_the_manifest(tree) -> None:
    root, folder = tree
    manifest = resolve_episode(CATALOG, root, "task_a", "episode_00000")
    _video(folder / "middle.mp4", 7)
    with pytest.raises(SourceDriftError):
        audit_episode(manifest, root, CATALOG)


def _catalog_file(tmp_path: Path) -> Path:
    path = tmp_path / "catalog.yaml"
    path.write_text(
        "schema_version: 1\ndataset_id: synthetic\nroot_variable: PRL_DATA_ROOT\n"
        f"layout: {CATALOG.layout}\n",
        encoding="utf-8",
    )
    return path


def _cli_args(tmp_path: Path, root: Path, *extra: str) -> list[str]:
    return [
        "data", "audit", "--manifest", str(tmp_path / "m.json"),
        "--catalog", str(_catalog_file(tmp_path)), "--data-root", str(root),
        "--output", str(tmp_path / "out" / "audit.json"), *extra,
    ]  # fmt: skip


def test_cli_audit_exit_codes_and_output_placement(tree, tmp_path: Path, capsys) -> None:
    root, folder = tree
    from plant_robotics.io.resolver import write_manifest

    write_manifest(
        resolve_episode(CATALOG, root, "task_a", "episode_00000"),
        tmp_path / "m.json",
        data_root=root,
    )
    main(_cli_args(tmp_path, root))  # exit 0 returns normally
    audit = json.loads((tmp_path / "out" / "audit.json").read_text(encoding="utf-8"))
    assert audit["summary"]["all_streams_complete"]
    assert audit["source_manifest_sha256"]

    with pytest.raises(SystemExit) as refused:  # existing output without --force
        main(_cli_args(tmp_path, root))
    assert refused.value.code == 2

    inside = _cli_args(tmp_path, root, "--force")
    inside[inside.index("--output") + 1] = str(root / "audit.json")
    with pytest.raises(SystemExit) as placed:
        main(inside)
    assert placed.value.code == 2 and not (root / "audit.json").exists()

    _video(folder / "left_arm.mp4", 8)  # drift -> exit 1, nothing decoded or written
    (tmp_path / "out" / "audit.json").unlink()
    with pytest.raises(SystemExit) as drift:
        main(_cli_args(tmp_path, root))
    assert drift.value.code == 1 and not (tmp_path / "out" / "audit.json").exists()
    assert "nothing decoded" in capsys.readouterr().out


def test_cli_audit_integrity_finding_exits_1_but_keeps_the_evidence(
    tree, tmp_path: Path, monkeypatch
) -> None:
    root, _ = tree
    from plant_robotics.io.resolver import write_manifest

    write_manifest(
        resolve_episode(CATALOG, root, "task_a", "episode_00000"),
        tmp_path / "m.json",
        data_root=root,
    )
    real = audit_module.audit_stream

    def short(path: Path, camera: str):
        record = real(path, camera)
        if camera == "middle":
            record["status"] = "incomplete"
        return record

    monkeypatch.setattr(audit_module, "audit_stream", short)
    with pytest.raises(SystemExit) as raised:
        main(_cli_args(tmp_path, root))
    assert raised.value.code == 1
    saved = json.loads((tmp_path / "out" / "audit.json").read_text(encoding="utf-8"))
    assert saved["summary"]["all_streams_complete"] is False
