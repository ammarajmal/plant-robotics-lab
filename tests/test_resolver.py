from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path

import cv2
import numpy as np
import pytest

from plant_robotics.domain.datasets import ManifestError
from plant_robotics.io.resolver import (
    Catalog,
    IdentityMismatchError,
    SourceResolutionError,
    SymlinkRedirectError,
    check_identity,
    load_catalog,
    load_manifest,
    resolve_data_root,
    resolve_episode,
    verify_episode,
    write_manifest,
)
from plant_robotics.io.video import VideoIngestionError

CAMERAS = ("left_arm", "middle", "right_arm")
LAYOUT = "ds/raw/{task_id}/{episode_id}/{camera_id}.mp4"
CATALOG = Catalog(dataset_id="synthetic", root_variable="PRL_DATA_ROOT", layout=LAYOUT)


def _video(path: Path, count: int = 4) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (32, 24))
    assert writer.isOpened()
    try:
        for index in range(count):
            writer.write(np.full((24, 32, 3), index, dtype=np.uint8))
    finally:
        writer.release()


def _tree(tmp_path: Path, task: str = "task_a", episode: str = "episode_00000") -> Path:
    root = tmp_path / "root"
    folder = root / "ds" / "raw" / task / episode
    folder.mkdir(parents=True)
    for camera in CAMERAS:
        _video(folder / f"{camera}.mp4")
    return root


def _listing(root: Path) -> list[tuple[str, int, int]]:
    return sorted(
        (str(p.relative_to(root)), p.stat().st_size, p.stat().st_mtime_ns) for p in root.rglob("*")
    )


def test_resolve_records_relative_paths_hashes_and_metadata(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    manifest = resolve_episode(CATALOG, root, "task_a", "episode_00000")

    assert [s.camera_id for s in manifest.streams] == list(CAMERAS)
    first = manifest.streams[0]
    assert first.relative_path == "ds/raw/task_a/episode_00000/left_arm.mp4"
    assert str(root) not in str(manifest.to_dict())
    path = root / first.relative_path
    assert first.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert first.size_bytes == path.stat().st_size
    assert (first.width, first.height, first.frame_count) == (32, 24, 4)
    assert manifest.dataset_id == "synthetic"
    assert manifest.root_variable == "PRL_DATA_ROOT"


def test_resolve_is_deterministic(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    one = resolve_episode(CATALOG, root, "task_a", "episode_00000")
    two = resolve_episode(CATALOG, root, "task_a", "episode_00000")
    assert one == two


def test_resolve_without_hashing_marks_hashes_unverified(tmp_path: Path) -> None:
    manifest = resolve_episode(
        CATALOG, _tree(tmp_path), "task_a", "episode_00000", compute_hash=False
    )
    assert all(stream.sha256 is None for stream in manifest.streams)


def test_resolve_never_modifies_the_data_root(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    before = _listing(root)
    resolve_episode(CATALOG, root, "task_a", "episode_00000")
    assert _listing(root) == before


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores permission bits")
def test_resolve_works_on_a_read_only_tree(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    paths = [root, *root.rglob("*")]
    try:
        for path in paths:
            path.chmod(stat.S_IMODE(path.stat().st_mode) & ~0o222)
        manifest = resolve_episode(CATALOG, root, "task_a", "episode_00000")
        assert len(manifest.streams) == 3
    finally:
        for path in paths:
            path.chmod(stat.S_IMODE(path.stat().st_mode) | 0o700)


def test_missing_root_file_root_and_missing_stream_are_errors(tmp_path: Path) -> None:
    with pytest.raises(SourceResolutionError, match="data root"):
        resolve_episode(CATALOG, tmp_path / "nope", "task_a", "episode_00000")
    not_a_dir = tmp_path / "file"
    not_a_dir.write_text("x")
    with pytest.raises(SourceResolutionError, match="data root"):
        resolve_episode(CATALOG, not_a_dir, "task_a", "episode_00000")
    root = _tree(tmp_path)
    (root / "ds/raw/task_a/episode_00000/middle.mp4").unlink()
    with pytest.raises(SourceResolutionError, match="middle"):
        resolve_episode(CATALOG, root, "task_a", "episode_00000")


def test_corrupt_video_is_rejected_not_hashed_into_a_manifest(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "ds/raw/task_a/episode_00000/middle.mp4").write_bytes(b"not a video")
    with pytest.raises(VideoIngestionError):
        resolve_episode(CATALOG, root, "task_a", "episode_00000")


def test_symlink_escaping_the_root_is_rejected(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    outside = tmp_path / "outside.mp4"
    _video(outside)
    link = root / "ds/raw/task_a/episode_00000/left_arm.mp4"
    link.unlink()
    link.symlink_to(outside)
    with pytest.raises(SourceResolutionError, match="outside"):
        resolve_episode(CATALOG, root, "task_a", "episode_00000")


@pytest.mark.parametrize("task_id", ["../x", "a/b", "", ".", "a b"])
def test_unsafe_identifiers_are_rejected_before_touching_the_filesystem(
    tmp_path: Path, task_id: str
) -> None:
    with pytest.raises(ManifestError):
        resolve_episode(CATALOG, tmp_path, task_id, "episode_00000")


def test_verify_matches_then_reports_each_kind_of_drift(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    manifest = resolve_episode(CATALOG, root, "task_a", "episode_00000")
    result = verify_episode(manifest, root)
    assert result.ok and result.hashes_checked and result.differences == ()

    folder = root / "ds/raw/task_a/episode_00000"
    with (folder / "left_arm.mp4").open("ab") as handle:
        handle.write(b"\0")
    (folder / "middle.mp4").unlink()
    _video(folder / "right_arm.mp4", count=6)
    drift = verify_episode(manifest, root).differences
    assert any("left_arm" in d and "size_bytes" in d for d in drift)
    assert any("left_arm" in d and "sha256" in d for d in drift)
    assert any("middle" in d and "unavailable" in d for d in drift)
    assert any("right_arm" in d and "frame_count" in d for d in drift)


def test_verify_without_hashing_says_hashes_were_not_checked(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    manifest = resolve_episode(CATALOG, root, "task_a", "episode_00000")
    result = verify_episode(manifest, root, compute_hash=False)
    assert result.ok and not result.hashes_checked


def test_manifest_write_is_deterministic_round_trips_and_refuses_the_data_root(
    tmp_path: Path,
) -> None:
    root = _tree(tmp_path)
    manifest = resolve_episode(CATALOG, root, "task_a", "episode_00000")
    out = tmp_path / "out" / "manifest.json"
    write_manifest(manifest, out, data_root=root)
    text = out.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert load_manifest(out) == manifest
    write_manifest(manifest, out, data_root=root, force=True)
    assert out.read_text(encoding="utf-8") == text

    with pytest.raises(SourceResolutionError, match="inside the data root"):
        write_manifest(manifest, root / "manifest.json", data_root=root)
    assert not (root / "manifest.json").exists()


def test_existing_manifest_is_refused_unless_forced(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    manifest = resolve_episode(CATALOG, root, "task_a", "episode_00000")
    out = tmp_path / "out" / "manifest.json"
    out.parent.mkdir()
    out.write_text("PRECIOUS", encoding="utf-8")
    with pytest.raises(SourceResolutionError, match="--force"):
        write_manifest(manifest, out, data_root=root)
    assert out.read_text(encoding="utf-8") == "PRECIOUS"
    assert [p.name for p in out.parent.iterdir()] == ["manifest.json"]

    write_manifest(manifest, out, data_root=root, force=True)
    assert load_manifest(out) == manifest
    assert [p.name for p in out.parent.iterdir()] == ["manifest.json"]


def test_failed_write_keeps_existing_manifest_and_leaves_no_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _tree(tmp_path)
    manifest = resolve_episode(CATALOG, root, "task_a", "episode_00000")
    out = tmp_path / "out" / "manifest.json"
    write_manifest(manifest, out, data_root=root)
    before = out.read_bytes()

    def explode(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("plant_robotics.io.resolver.os.replace", explode)
    with pytest.raises(OSError, match="disk full"):
        write_manifest(manifest, out, data_root=root, force=True)
    assert out.read_bytes() == before
    assert [p.name for p in out.parent.iterdir()] == ["manifest.json"]


def test_output_symlinks_and_odd_names_are_refused(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    manifest = resolve_episode(CATALOG, root, "task_a", "episode_00000")
    out = tmp_path / "out"
    out.mkdir()
    victim = tmp_path / "victim.json"
    victim.write_text("KEEP", encoding="utf-8")

    (out / "link.json").symlink_to(victim)
    for force in (False, True):
        with pytest.raises(SourceResolutionError, match="symlink"):
            write_manifest(manifest, out / "link.json", data_root=root, force=force)
    assert victim.read_text(encoding="utf-8") == "KEEP"

    (out / "dangling.json").symlink_to(tmp_path / "does-not-exist.json")
    with pytest.raises(SourceResolutionError, match="symlink"):
        write_manifest(manifest, out / "dangling.json", data_root=root, force=True)
    assert not (tmp_path / "does-not-exist.json").exists()

    (out / "into_root").symlink_to(root)
    with pytest.raises(SourceResolutionError, match="inside the data root"):
        write_manifest(manifest, out / "into_root" / "m.json", data_root=root)
    assert not (root / "m.json").exists()

    for name in (out / "..", out / ".", out):
        with pytest.raises(SourceResolutionError):
            write_manifest(manifest, name, data_root=root, force=True)


def test_load_manifest_rejects_invalid_json_and_contract_violations(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    with pytest.raises(ManifestError, match="invalid JSON"):
        load_manifest(bad)
    bad.write_text("[]", encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(bad)
    with pytest.raises(FileNotFoundError):
        load_manifest(tmp_path / "missing.json")
    bad.write_bytes(b"\xff\xfe\x00{")
    with pytest.raises(ManifestError, match="UTF-8"):
        load_manifest(bad)


def test_load_catalog_rejects_non_utf8(tmp_path: Path) -> None:
    path = tmp_path / "catalog.yaml"
    path.write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(ManifestError, match="UTF-8"):
        load_catalog(path)


def _catalog_file(tmp_path: Path, layout: str, **extra: str) -> Path:
    lines = ["schema_version: 1", "dataset_id: synthetic", "root_variable: PRL_DATA_ROOT"]
    lines += [f"{k}: {v}" for k, v in extra.items()]
    lines.append(f"layout: {layout}")
    path = tmp_path / "catalog.yaml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_load_catalog_accepts_the_expected_layout(tmp_path: Path) -> None:
    assert load_catalog(_catalog_file(tmp_path, LAYOUT)) == CATALOG


@pytest.mark.parametrize(
    "layout",
    [
        "/abs/{task_id}/{episode_id}/{camera_id}.mp4",
        "../{task_id}/{episode_id}/{camera_id}.mp4",
        "ds/{task_id}/{episode_id}.mp4",
        "ds/{task_id}/{episode_id}/{camera_id}/{other}.mp4",
        "ds/{task_id.__class__}/{episode_id}/{camera_id}.mp4",
        "ds/{task_id!r}/{episode_id}/{camera_id}.mp4",
        "ds/{task_id:>9}/{episode_id}/{camera_id}.mp4",
    ],
)
def test_load_catalog_rejects_unsafe_layouts(tmp_path: Path, layout: str) -> None:
    with pytest.raises(ManifestError):
        load_catalog(_catalog_file(tmp_path, f"'{layout}'"))


def test_load_catalog_rejects_bad_structure(tmp_path: Path) -> None:
    path = tmp_path / "catalog.yaml"
    path.write_text("- a\n", encoding="utf-8")
    with pytest.raises(ManifestError, match="mapping"):
        load_catalog(path)
    with pytest.raises(ManifestError, match="unexpected"):
        load_catalog(_catalog_file(tmp_path, LAYOUT, surprise="1"))
    path.write_text("a: [", encoding="utf-8")
    with pytest.raises(ManifestError, match="invalid YAML"):
        load_catalog(path)


def test_resolve_data_root_prefers_argument_then_environment(tmp_path: Path) -> None:
    env = {"PRL_DATA_ROOT": str(tmp_path / "env")}
    assert resolve_data_root(tmp_path / "arg", "PRL_DATA_ROOT", env) == tmp_path / "arg"
    assert resolve_data_root(None, "PRL_DATA_ROOT", env) == tmp_path / "env"
    with pytest.raises(SourceResolutionError, match="PRL_DATA_ROOT"):
        resolve_data_root(None, "PRL_DATA_ROOT", {})
    with pytest.raises(SourceResolutionError, match="PRL_DATA_ROOT"):
        resolve_data_root(None, "PRL_DATA_ROOT", {"PRL_DATA_ROOT": "  "})


# --- identity binding (R-004-3) -------------------------------------------------


def _manifest(tmp_path: Path):
    root = _tree(tmp_path)
    return root, resolve_episode(CATALOG, root, "task_a", "episode_00000")


def _with(manifest, **fields):
    from dataclasses import replace

    return replace(manifest, **fields)


def _with_stream(manifest, index: int, **fields):
    from dataclasses import replace

    streams = list(manifest.streams)
    streams[index] = replace(streams[index], **fields)
    return _with(manifest, streams=tuple(streams))


def test_matching_identity_verifies_with_catalog(tmp_path: Path) -> None:
    root, manifest = _manifest(tmp_path)
    check_identity(manifest, CATALOG)
    assert verify_episode(manifest, root, catalog=CATALOG).ok


@pytest.mark.parametrize(
    "mutate",
    [
        lambda m: _with(m, dataset_id="other"),
        lambda m: _with(m, root_variable="OTHER_ROOT"),
        lambda m: _with(m, episode_id="episode_00001"),
        lambda m: _with(m, task_id="task_b"),
        lambda m: _with_stream(m, 1, relative_path=m.streams[0].relative_path),  # camera swap
        lambda m: _with_stream(
            m, 0, relative_path="ds/raw/task_a/episode_00001/left_arm.mp4"
        ),  # other episode
        lambda m: _with_stream(m, 2, relative_path="ds/raw/task_a/episode_00000/right_arm.MP4"),
        lambda m: _with_stream(m, 0, relative_path="elsewhere/left_arm.mp4"),
    ],
)
def test_identity_mismatches_are_rejected(tmp_path: Path, mutate) -> None:
    root, manifest = _manifest(tmp_path)
    with pytest.raises(IdentityMismatchError):
        verify_episode(mutate(manifest), root, catalog=CATALOG)


def test_different_catalog_layout_is_rejected(tmp_path: Path) -> None:
    root, manifest = _manifest(tmp_path)
    other = Catalog("synthetic", "PRL_DATA_ROOT", "ds/{task_id}/{episode_id}/{camera_id}.mp4")
    with pytest.raises(IdentityMismatchError):
        verify_episode(manifest, root, catalog=other)


def test_in_root_symlink_to_another_camera_or_episode_is_rejected(tmp_path: Path) -> None:
    root, manifest = _manifest(tmp_path)
    folder = root / "ds/raw/task_a/episode_00000"
    other = root / "ds/raw/task_a/episode_00001"
    other.mkdir(parents=True)
    _video(other / "left_arm.mp4", 4)

    middle = folder / "middle.mp4"
    middle.unlink()
    middle.symlink_to(folder / "left_arm.mp4")  # another camera, same bytes as left
    with pytest.raises(SymlinkRedirectError, match="redirected"):
        verify_episode(manifest, root, catalog=CATALOG)
    with pytest.raises(SymlinkRedirectError):
        resolve_episode(CATALOG, root, "task_a", "episode_00000")

    middle.unlink()
    _video(middle)
    left = folder / "left_arm.mp4"
    left.unlink()
    left.symlink_to(other / "left_arm.mp4")  # another episode
    with pytest.raises(SymlinkRedirectError):
        verify_episode(manifest, root, catalog=CATALOG)


def test_symlinked_directory_and_chains_are_rejected(tmp_path: Path) -> None:
    root, manifest = _manifest(tmp_path)
    raw = root / "ds/raw"
    real = root / "ds/real_task_a"
    (raw / "task_a").rename(real)
    (raw / "task_a").symlink_to(real)
    with pytest.raises(SymlinkRedirectError):
        verify_episode(manifest, root, catalog=CATALOG)


def test_cli_maps_identity_and_redirect_errors_to_exit_2(tmp_path: Path) -> None:
    from plant_robotics.cli import main

    root, manifest = _manifest(tmp_path)
    out = tmp_path / "m.json"
    write_manifest(manifest, out, data_root=root)
    catalog = _catalog_file(tmp_path, "ds/other/{task_id}/{episode_id}/{camera_id}.mp4")
    argv = ["data", "verify", "--manifest", str(out), "--data-root", str(root)]
    main(argv)  # without a catalog: unchanged behaviour, exit 0
    with pytest.raises(SystemExit) as raised:
        main([*argv, "--catalog", str(catalog)])
    assert raised.value.code == 2
