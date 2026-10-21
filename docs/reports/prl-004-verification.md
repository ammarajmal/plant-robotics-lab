# PRL-004 verification record

Branch `feat/prl-004-data-source-resolver`; evidence collected at `7d5b5e8`
plus the documentation and manifest added in the final commit.

Environment: Python 3.12.13, NumPy 2.5.4, OpenCV 5.0.0 (`opencv-python-headless`),
PyYAML 6.0.3 (uv-managed `.venv`).

## Automated checks (run 2026-10-21, at the original evidence commit)

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
(`04_PROJECTS/norman_blue_tape_full/results/p1/episode_00000_stream_audit.csv`
under the NORMAN root; NORMAN's own result, not produced by PRL): SHA-256,
width, height, fps, and container-metadata frame count (`frame_count_meta`)
agree for `left_arm`, `middle`, and `right_arm`. The audit's own decoded count
(`frame_count_decoded`, 526) is NORMAN's result. PRL did not decode any frames,
so PRL's agreement is a metadata and byte-identity match, not an independent
decode check.

NORMAN's Git status was captured before and after the run and was identical;
NORMAN's working tree was already dirty before this task.

## Not established

Camera exposure synchronization, frame-timestamp accuracy, calibration,
cross-view identity, tracking, 3D geometry, licence/reuse permission for NORMAN
code, and playback of this real episode (not run in PRL-004).

## Post-review remediation (2026-10-21)

An independent review found: (M1) NUL bytes in a manifest path and non-UTF-8
manifests/catalogs escaped as uncaught exceptions, exiting 1 (the drift code);
(minor) `resolve` silently overwrote an existing output. Both are fixed with
regression tests; the NORMAN audit path above was corrected. Open items
(TOCTOU, symlink retargeting, manifest-to-catalog binding, duplicate YAML keys)
are in `docs/planning/risk_register.md`.

Re-run after the fixes (`.venv`, Python 3.12.13):

```text
pytest -q                          -> 91 passed
ruff check .                       -> all checks passed
ruff format --check .              -> 50 files already formatted
compileall -q src tests            -> exit 0
uv lock --check                    -> Resolved 11 packages (lock current)
git diff --check 67f0acc..HEAD     -> exit 0
prl data verify (real episode)     -> manifest matches ..., exit 0
```

The earlier "79 passed / 47 files" figures describe the original evidence commit.
NORMAN's full `git status --porcelain=v2 --branch -uall` output, HEAD, and
`git diff` hash were byte-identical before and after (NORMAN remained dirty from
before this task).
