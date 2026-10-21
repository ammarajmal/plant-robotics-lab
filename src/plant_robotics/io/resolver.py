"""Read-only resolution of dataset episodes into portable source manifests.

The resolver locates three-view episodes beneath a caller-supplied data root,
records observed facts (size, SHA-256, decoder metadata), and never copies,
moves, or writes anything beneath that root. A manifest is evidence of what
was observed when it was produced, not proof that the media is correct, and it
makes no synchronization claim.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from string import Formatter
from typing import Final

import yaml

from plant_robotics.domain.datasets import (
    CAMERA_ORDER,
    SCHEMA_VERSION,
    ManifestError,
    SourceManifest,
    StreamRecord,
    validate_identifier,
    validate_relative_path,
)
from plant_robotics.io.hashing import sha256_file
from plant_robotics.io.video import VideoIngestionError, inspect_video

_PLACEHOLDERS: Final = frozenset({"task_id", "episode_id", "camera_id"})
_CATALOG_KEYS: Final = {"schema_version", "dataset_id", "root_variable", "layout"}


class SourceResolutionError(ValueError):
    """A data root, path, or output location cannot be used safely."""


@dataclass(frozen=True, slots=True)
class Catalog:
    """How one dataset arranges episode videos beneath its data root."""

    dataset_id: str
    root_variable: str
    layout: str

    def relative_path(self, task_id: str, episode_id: str, camera_id: str) -> str:
        return validate_relative_path(
            self.layout.format(task_id=task_id, episode_id=episode_id, camera_id=camera_id)
        )


def _check_layout(layout: object) -> str:
    if not isinstance(layout, str):
        raise ManifestError(f"layout must be a string, got {layout!r}")
    try:
        parsed = list(Formatter().parse(layout))
    except ValueError as exc:
        raise ManifestError(f"layout is not a valid template: {exc}") from exc
    fields = set()
    for _, field, spec, conversion in parsed:
        if field is None:
            continue
        if field not in _PLACEHOLDERS or spec or conversion:
            raise ManifestError(
                f"layout may only use plain {sorted(_PLACEHOLDERS)} placeholders, got {field!r}"
            )
        fields.add(field)
    if fields != _PLACEHOLDERS:
        raise ManifestError(f"layout must use exactly {sorted(_PLACEHOLDERS)}")
    validate_relative_path(layout.format(task_id="t", episode_id="e", camera_id="c"))
    return layout


def load_catalog(path: Path) -> Catalog:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ManifestError(f"invalid YAML: {path}") from exc
    if not isinstance(raw, dict):
        raise ManifestError("catalog root must be a mapping")
    if raw.keys() - _CATALOG_KEYS:
        raise ManifestError(f"catalog has unexpected keys: {sorted(raw.keys() - _CATALOG_KEYS)}")
    if _CATALOG_KEYS - raw.keys():
        raise ManifestError(f"catalog is missing keys: {sorted(_CATALOG_KEYS - raw.keys())}")
    if raw["schema_version"] != SCHEMA_VERSION:
        raise ManifestError(f"schema_version must be {SCHEMA_VERSION}")
    return Catalog(
        dataset_id=validate_identifier(raw["dataset_id"], "dataset_id"),
        root_variable=validate_identifier(raw["root_variable"], "root_variable"),
        layout=_check_layout(raw["layout"]),
    )


def resolve_data_root(
    argument: Path | None, variable: str, environ: Mapping[str, str] | None = None
) -> Path:
    """Prefer the explicit argument, then the named environment variable."""

    if argument is not None:
        return Path(argument)
    value = (os.environ if environ is None else environ).get(variable, "").strip()
    if not value:
        raise SourceResolutionError(f"no data root: pass --data-root or set {variable}")
    return Path(value)


def _open_root(data_root: Path) -> Path:
    root = Path(data_root).resolve()
    if not root.is_dir():
        raise SourceResolutionError(f"data root is not a directory: {root}")
    return root


def _locate(root: Path, relative_path: str, camera: str) -> Path:
    """Resolve symlinks and require the file to stay inside the root."""

    resolved = (root / relative_path).resolve()
    if not resolved.is_relative_to(root):
        raise SourceResolutionError(f"{camera}: path resolves outside the data root")
    if not resolved.is_file():
        raise SourceResolutionError(f"{camera}: source file not found: {relative_path}")
    return resolved


def _observe(root: Path, relative_path: str, camera: str, *, compute_hash: bool) -> StreamRecord:
    path = _locate(root, relative_path, camera)
    info = inspect_video(path, camera)
    return StreamRecord(
        camera_id=info.camera_id,
        relative_path=relative_path,
        size_bytes=path.stat().st_size,
        sha256=sha256_file(path) if compute_hash else None,
        width=info.width,
        height=info.height,
        fps=info.fps,
        frame_count=info.frame_count,
        codec=info.codec,
        backend=info.backend,
    )


def resolve_episode(
    catalog: Catalog,
    data_root: Path,
    task_id: str,
    episode_id: str,
    *,
    compute_hash: bool = True,
) -> SourceManifest:
    """Observe one episode's three streams without modifying anything."""

    validate_identifier(task_id, "task_id")
    validate_identifier(episode_id, "episode_id")
    root = _open_root(data_root)
    streams = tuple(
        _observe(
            root,
            catalog.relative_path(task_id, episode_id, camera),
            camera,
            compute_hash=compute_hash,
        )
        for camera in CAMERA_ORDER
    )
    return SourceManifest(
        dataset_id=catalog.dataset_id,
        task_id=task_id,
        episode_id=episode_id,
        root_variable=catalog.root_variable,
        streams=streams,  # type: ignore[arg-type]
    )


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Differences between a manifest and the files currently under a data root."""

    differences: tuple[str, ...]
    hashes_checked: bool

    @property
    def ok(self) -> bool:
        return not self.differences


def verify_episode(
    manifest: SourceManifest, data_root: Path, *, compute_hash: bool = True
) -> VerificationResult:
    """Compare recorded facts with current files; ``backend`` is not compared.

    File-level facts (size, hash) are checked before decoding so a file that
    changed and no longer decodes is still reported as changed.
    """

    root = _open_root(data_root)
    differences: list[str] = []

    def compare(camera: str, name: str, recorded: object, observed: object) -> None:
        if recorded != observed:
            differences.append(f"{camera}: {name} recorded {recorded!r}, observed {observed!r}")

    for stream in manifest.streams:
        camera = stream.camera_id
        try:
            path = _locate(root, stream.relative_path, camera)
        except SourceResolutionError as exc:
            differences.append(f"{exc} (unavailable)")
            continue
        compare(camera, "size_bytes", stream.size_bytes, path.stat().st_size)
        if compute_hash and stream.sha256 is not None:
            compare(camera, "sha256", stream.sha256, sha256_file(path))
        try:
            info = inspect_video(path, camera)
        except VideoIngestionError as exc:
            differences.append(f"{camera}: no longer decodes: {exc}")
            continue
        compare(camera, "width", stream.width, info.width)
        compare(camera, "height", stream.height, info.height)
        compare(camera, "fps", stream.fps, info.fps)
        compare(camera, "frame_count", stream.frame_count, info.frame_count)
        compare(camera, "codec", stream.codec, info.codec)
    hashes_checked = compute_hash and all(s.sha256 is not None for s in manifest.streams)
    return VerificationResult(tuple(differences), hashes_checked)


def write_manifest(manifest: SourceManifest, path: Path, *, data_root: Path) -> None:
    """Write deterministic JSON, refusing any location inside the data root."""

    root = Path(data_root).resolve()
    target = Path(path).resolve()
    if target.is_relative_to(root):
        raise SourceResolutionError(f"refusing to write inside the data root: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def load_manifest(path: Path) -> SourceManifest:
    text = Path(path).read_text(encoding="utf-8")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestError(f"invalid JSON: {path}") from exc
    return SourceManifest.from_dict(raw)
