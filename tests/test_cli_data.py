from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from plant_robotics.cli import main

CAMERAS = ("left_arm", "middle", "right_arm")


def _video(path: Path) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (32, 24))
    assert writer.isOpened()
    try:
        for index in range(4):
            writer.write(np.full((24, 32, 3), index, dtype=np.uint8))
    finally:
        writer.release()


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Path]:
    root = tmp_path / "root"
    folder = root / "ds" / "raw" / "task_a" / "episode_00000"
    folder.mkdir(parents=True)
    for camera in CAMERAS:
        _video(folder / f"{camera}.mp4")
    catalog = tmp_path / "catalog.yaml"
    catalog.write_text(
        "schema_version: 1\ndataset_id: synthetic\nroot_variable: PRL_DATA_ROOT\n"
        "layout: ds/raw/{task_id}/{episode_id}/{camera_id}.mp4\n",
        encoding="utf-8",
    )
    return {"root": root, "catalog": catalog, "out": tmp_path / "out" / "manifest.json"}


def _resolve(s: dict[str, Path], *extra: str) -> None:
    main(
        [
            "data",
            "resolve",
            "--catalog",
            str(s["catalog"]),
            "--task-id",
            "task_a",
            "--episode-id",
            "episode_00000",
            "--output",
            str(s["out"]),
            "--data-root",
            str(s["root"]),
            *extra,
        ]
    )


def test_resolve_then_verify_succeeds(
    setup: dict[str, Path], capsys: pytest.CaptureFixture
) -> None:
    _resolve(setup)
    assert "SHA-256 recorded" in capsys.readouterr().out
    manifest = json.loads(setup["out"].read_text(encoding="utf-8"))
    assert manifest["alignment"]["exposure_synchronization"] == "unverified"

    main(["data", "verify", "--manifest", str(setup["out"]), "--data-root", str(setup["root"])])
    assert "sizes, hashes, metadata" in capsys.readouterr().out


def test_verify_uses_the_environment_variable_named_in_the_manifest(
    setup: dict[str, Path], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    _resolve(setup)
    monkeypatch.setenv("PRL_DATA_ROOT", str(setup["root"]))
    main(["data", "verify", "--manifest", str(setup["out"])])
    assert "matches" in capsys.readouterr().out


def test_no_hash_is_reported_as_unverified_everywhere(
    setup: dict[str, Path], capsys: pytest.CaptureFixture
) -> None:
    _resolve(setup, "--no-hash")
    assert "unverified (no hashes)" in capsys.readouterr().out
    main(["data", "verify", "--manifest", str(setup["out"]), "--data-root", str(setup["root"])])
    assert "hashes NOT checked" in capsys.readouterr().out


def test_verify_exit_code_1_on_drift(setup: dict[str, Path], capsys: pytest.CaptureFixture) -> None:
    _resolve(setup)
    capsys.readouterr()
    target = setup["root"] / "ds/raw/task_a/episode_00000/middle.mp4"
    target.write_bytes(target.read_bytes() + b"\0")
    with pytest.raises(SystemExit) as raised:
        main(["data", "verify", "--manifest", str(setup["out"]), "--data-root", str(setup["root"])])
    assert raised.value.code == 1
    assert "middle: size_bytes" in capsys.readouterr().out


def test_errors_exit_2_with_a_message(
    setup: dict[str, Path], capsys: pytest.CaptureFixture
) -> None:
    setup["out"] = setup["root"] / "manifest.json"
    with pytest.raises(SystemExit) as raised:
        _resolve(setup)
    assert raised.value.code == 2
    assert "inside the data root" in capsys.readouterr().err
    assert not setup["out"].exists()

    with pytest.raises(SystemExit) as raised:
        main(["data", "verify", "--manifest", str(setup["root"] / "missing.json")])
    assert raised.value.code == 2


def test_missing_data_root_names_the_variable(
    setup: dict[str, Path], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.delenv("PRL_DATA_ROOT", raising=False)
    with pytest.raises(SystemExit) as raised:
        main(
            [
                "data",
                "resolve",
                "--catalog",
                str(setup["catalog"]),
                "--task-id",
                "task_a",
                "--episode-id",
                "episode_00000",
                "--output",
                str(setup["out"]),
            ]
        )
    assert raised.value.code == 2
    assert "PRL_DATA_ROOT" in capsys.readouterr().err


def test_status_and_playback_usage_are_unchanged(capsys: pytest.CaptureFixture) -> None:
    main(["status"])
    assert "installed" in capsys.readouterr().out
    with pytest.raises(SystemExit) as raised:
        main(["playback"])
    assert raised.value.code == 2
    assert "playback requires" in capsys.readouterr().err
