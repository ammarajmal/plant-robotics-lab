# PRL-004 verification record

Branch `feat/prl-004-data-source-resolver`; evidence collected at `7d5b5e8`
plus the documentation and manifest added in the final commit.

Environment: Python 3.12.13, NumPy 2.5.4, OpenCV 5.0.0 (`opencv-python-headless`),
PyYAML 6.0.3 (uv-managed `.venv`).

## Automated checks (run 2026-10-21)

```text
uv run pytest -q                    -> 79 passed
uv run ruff check .                 -> exit 0
uv run ruff format --check .        -> 47 files already formatted
uv run python -m compileall -q ...  -> exit 0
uv lock --check                     -> Resolved 11 packages (lock current)
git diff --check                    -> exit 0
```

Tests are synthetic (tiny `mp4v` videos in temporary directories). They cover
manifest validation and round trips, path traversal and symlink escape,
read-only trees, unchanged data-root listings, drift reporting, catalog
rejection cases, and CLI exit codes.

## Real-data run (read-only)

Data root: the `PRL_DATA_ROOT` value from `.env.example`
(`.../norman/datasets`). Episode: `leaf_removal_point_blue/episode_00000`.

```text
prl data resolve ...  -> manifest written [SHA-256 recorded]
prl data verify ...   -> manifest matches current files: sizes, hashes, metadata
```

PRL-observed values for all three streams: 640x480, 30.0 fps, 526 frames
(container metadata), h264, backend FFMPEG. The committed manifest is
`data_manifests/norman_leaf_removal_point_blue_episode_00000.json`.

Comparison with NORMAN's historical stream audit
(`results/p1/episode_00000_stream_audit.csv`, NORMAN's own result, not produced
by PRL): SHA-256, width, fps, and frame count agree for `left_arm`, `middle`,
and `right_arm`. PRL did not decode all frames, so agreement with the audit's
*decoded* frame count is a metadata match, not an independent decode check.

NORMAN's Git status was captured before and after the run and was identical;
NORMAN's working tree was already dirty before this task.

## Not established

Camera exposure synchronization, frame-timestamp accuracy, calibration,
cross-view identity, tracking, 3D geometry, licence/reuse permission for NORMAN
code, and playback of this real episode (not run in PRL-004).
