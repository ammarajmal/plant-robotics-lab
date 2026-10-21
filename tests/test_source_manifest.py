from __future__ import annotations

import json
from dataclasses import replace

import pytest

from plant_robotics.domain.datasets import (
    ManifestError,
    SourceManifest,
    StreamRecord,
    validate_identifier,
    validate_relative_path,
)

SHA = "a" * 64


def _stream(camera: str = "left_arm", **overrides: object) -> StreamRecord:
    values: dict[str, object] = {
        "camera_id": camera,
        "relative_path": f"task/episode_00000/{camera}.mp4",
        "size_bytes": 10,
        "sha256": SHA,
        "width": 640,
        "height": 480,
        "fps": 30.0,
        "frame_count": 526,
        "codec": "h264",
        "backend": "FFMPEG",
    }
    values.update(overrides)
    return StreamRecord(**values)  # type: ignore[arg-type]


def _manifest(**overrides: object) -> SourceManifest:
    values: dict[str, object] = {
        "dataset_id": "norman-internship-2026",
        "task_id": "leaf_removal_point_blue",
        "episode_id": "episode_00000",
        "root_variable": "PRL_DATA_ROOT",
        "streams": tuple(_stream(camera) for camera in ("left_arm", "middle", "right_arm")),
    }
    values.update(overrides)
    return SourceManifest(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["a/b.mp4", "episode_00000", "x.y/z"])
def test_relative_path_accepts_normalized_posix_paths(value: str) -> None:
    assert validate_relative_path(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "/abs/a.mp4",
        "../a.mp4",
        "a/../b",
        "a//b",
        "./a",
        "a\\b",
        "a/",
        "C:\\a",
        "a\x00b.mp4",
        "\x00",
    ],
)
def test_relative_path_rejects_absolute_traversal_and_non_normalized(value: str) -> None:
    with pytest.raises(ManifestError):
        validate_relative_path(value)


@pytest.mark.parametrize("value", ["", ".", "..", "a/b", "a b", "-x", "a\\b", "é"])
def test_identifier_rejects_separators_and_odd_characters(value: str) -> None:
    with pytest.raises(ManifestError):
        validate_identifier(value, "task_id")


def test_stream_rejects_unknown_camera_and_bad_numbers() -> None:
    with pytest.raises(ManifestError, match="camera_id"):
        _stream("rear")
    for field, bad in (
        ("width", 0),
        ("height", -1),
        ("frame_count", 0),
        ("fps", 0.0),
        ("fps", float("nan")),
        ("size_bytes", -1),
        ("sha256", "XYZ"),
        ("sha256", "A" * 64),
    ):
        with pytest.raises(ManifestError):
            _stream(**{field: bad})


def test_stream_allows_unhashed_sha256_as_none() -> None:
    assert _stream(sha256=None).sha256 is None


def test_manifest_requires_three_ordered_views() -> None:
    streams = _manifest().streams
    with pytest.raises(ManifestError, match="ordered"):
        _manifest(streams=(streams[1], streams[0], streams[2]))
    with pytest.raises(ManifestError, match="three"):
        _manifest(streams=streams[:2])


def test_manifest_round_trips_through_json_and_is_deterministic() -> None:
    manifest = _manifest()
    first = json.dumps(manifest.to_dict(), sort_keys=True)
    restored = SourceManifest.from_dict(json.loads(first))
    assert restored == manifest
    assert json.dumps(restored.to_dict(), sort_keys=True) == first


def test_manifest_dict_states_alignment_is_unverified() -> None:
    alignment = _manifest().to_dict()["alignment"]
    assert alignment["exposure_synchronization"] == "unverified"
    assert alignment["timestamp_provenance"] == "nominal_frame_index"


def test_from_dict_rejects_unknown_keys_versions_and_tampered_alignment() -> None:
    raw = _manifest().to_dict()
    with pytest.raises(ManifestError, match="schema_version"):
        SourceManifest.from_dict({**raw, "schema_version": 2})
    with pytest.raises(ManifestError, match="unexpected"):
        SourceManifest.from_dict({**raw, "extra": 1})
    with pytest.raises(ManifestError, match="alignment"):
        SourceManifest.from_dict(
            {**raw, "alignment": {**raw["alignment"], "exposure_synchronization": "verified"}}
        )
    with pytest.raises(ManifestError, match="missing"):
        SourceManifest.from_dict({k: v for k, v in raw.items() if k != "episode_id"})
    with pytest.raises(ManifestError):
        SourceManifest.from_dict("not a mapping")  # type: ignore[arg-type]


def test_from_dict_rejects_malformed_stream_entries() -> None:
    raw = _manifest().to_dict()
    bad_stream = {**raw["streams"][0], "relative_path": "../escape.mp4"}
    with pytest.raises(ManifestError):
        SourceManifest.from_dict({**raw, "streams": [bad_stream, *raw["streams"][1:]]})
    with pytest.raises(ManifestError, match="unexpected"):
        SourceManifest.from_dict(
            {**raw, "streams": [{**raw["streams"][0], "x": 1}, *raw["streams"][1:]]}
        )


def test_records_are_immutable() -> None:
    manifest = _manifest()
    with pytest.raises(AttributeError):
        manifest.episode_id = "other"  # type: ignore[misc]
    assert replace(manifest, episode_id="episode_00001").episode_id == "episode_00001"
