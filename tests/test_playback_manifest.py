from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from plant_robotics.cli import main
from plant_robotics.io.resolver import Catalog, resolve_episode, write_manifest
from plant_robotics.playback.config import ConfigError, load_config
from plant_robotics.playback.render import render_three_view

CAMERAS = ("left_arm", "middle", "right_arm")
LAYOUT = "ds/raw/{task_id}/{episode_id}/{camera_id}.mp4"
CATALOG = Catalog("synthetic", "PRL_DATA_ROOT", LAYOUT)


def _video(path: Path, count: int = 4) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (32, 24))
    for index in range(count):
        writer.write(np.full((24, 32, 3), index * 10, dtype=np.uint8))
    writer.release()


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Path]:
    root = tmp_path / "root"
    folder = root / "ds/raw/task_a/episode_00000"
    folder.mkdir(parents=True)
    for camera in CAMERAS:
        _video(folder / f"{camera}.mp4")
    work = tmp_path / "work"
    work.mkdir()
    write_manifest(
        resolve_episode(CATALOG, root, "task_a", "episode_00000"), work / "m.json", data_root=root
    )
    (work / "catalog.yaml").write_text(
        f"schema_version: 1\ndataset_id: synthetic\nroot_variable: PRL_DATA_ROOT\nlayout: {LAYOUT}\n",
        encoding="utf-8",
    )
    config = work / "config.yaml"
    config.write_text(
        "schema_version: 1\ndataset_id: synthetic\nepisode_id: episode_00000\n"
        "run_id: r1\noutput_dir: out\n"
        "source_manifest:\n  manifest: m.json\n  catalog: catalog.yaml\n",
        encoding="utf-8",
    )
    return {"root": root, "folder": folder, "work": work, "config": config}


def test_playback_selects_inputs_from_a_verified_manifest(setup) -> None:
    config = load_config(setup["config"], data_root=setup["root"])
    assert [v.camera_id for v in config.views] == list(CAMERAS)
    manifest = render_three_view(config)
    assert manifest["execution"]["status"] == "success"
    assert manifest["source_manifest"]["sha256"] == config.source_manifest_sha256
    for stream in manifest["streams"]:
        assert stream["source"].startswith("data-root-relative:ds/raw/task_a/episode_00000/")
        assert str(setup["root"]) not in json.dumps(manifest)
    assert manifest["alignment"]["exposure_synchronization"] == "unverified"


def test_views_and_source_manifest_are_mutually_exclusive(setup) -> None:
    text = setup["config"].read_text(encoding="utf-8") + "views: []\n"
    setup["config"].write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError, match="not both"):
        load_config(setup["config"], data_root=setup["root"])


def test_config_naming_a_different_episode_is_rejected(setup) -> None:
    text = setup["config"].read_text(encoding="utf-8").replace("episode_00000", "episode_00009", 1)
    setup["config"].write_text(text, encoding="utf-8")
    with pytest.raises(ConfigError, match="episode_00009"):
        load_config(setup["config"], data_root=setup["root"])


def test_drifted_source_is_rejected_before_any_output(setup) -> None:
    _video(setup["folder"] / "middle.mp4", 6)
    with pytest.raises(ConfigError, match="differs"):
        load_config(setup["config"], data_root=setup["root"])
    assert not (setup["work"] / "out").exists()


def test_symlink_redirect_and_wrong_catalog_are_rejected(setup) -> None:
    middle = setup["folder"] / "middle.mp4"
    middle.unlink()
    middle.symlink_to(setup["folder"] / "left_arm.mp4")
    with pytest.raises(ConfigError, match="redirected"):
        load_config(setup["config"], data_root=setup["root"])
    middle.unlink()
    _video(middle)  # restore, different bytes: still must not be silently accepted
    other = setup["work"] / "catalog.yaml"
    other.write_text(
        other.read_text(encoding="utf-8").replace("ds/raw", "ds/other"), encoding="utf-8"
    )
    with pytest.raises(ConfigError, match="rejected"):
        load_config(setup["config"], data_root=setup["root"])


def test_cli_playback_from_manifest_and_exit_2_on_rejection(setup, capsys) -> None:
    argv = [
        "playback",
        "three-view",
        "--config",
        str(setup["config"]),
        "--data-root",
        str(setup["root"]),
    ]
    main(argv)
    assert (setup["work"] / "out" / "three_view.mp4").is_file()
    (setup["folder"] / "right_arm.mp4").write_bytes(b"x")
    with pytest.raises(SystemExit) as raised:
        main(argv)
    assert raised.value.code == 2
    assert "source manifest" in capsys.readouterr().err
