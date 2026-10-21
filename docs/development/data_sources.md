# Data-source resolution (PRL-004)

PRL references large datasets in place. A **source manifest** records where an
episode's three videos live (relative to a data root), plus facts observed when
the manifest was made. Nothing is copied, and nothing is written beneath the
data root.

## Use

```bash
export PRL_DATA_ROOT=/path/to/norman/datasets      # or pass --data-root
prl data resolve --catalog configs/data/norman_catalog.yaml \
  --task-id leaf_removal_point_blue --episode-id episode_00000 \
  --output data_manifests/norman_leaf_removal_point_blue_episode_00000.json
prl data verify --manifest data_manifests/norman_leaf_removal_point_blue_episode_00000.json
```

`verify` exits 0 when files match, 1 on drift (differences are printed), and 2
on invalid input or execution errors (malformed or non-UTF-8 manifests and
catalogs, NUL bytes in paths, missing files or roots). An uncaught exception
would exit 1, so errors are mapped to 2 at the CLI boundary; only the project's
own exceptions and `OSError` are caught there.

`resolve` refuses to overwrite an existing `--output` (pass `--force` to
replace it) and refuses a destination that is a symlink. The manifest is
written to a temporary file beside the destination and published atomically, so
a failed write leaves any existing manifest intact. `--no-hash` skips SHA-256 on large trees; the output then says
hashes were not checked and the manifest records `sha256: null` (unverified,
never "unchanged").

## Design

- `domain/datasets.py`: plain records (`StreamRecord`, `SourceManifest`) with
  strict validation. No filesystem access, so the contract is testable alone.
- `io/resolver.py`: the adapter. It reads the catalog (`configs/data/`), finds
  files, and reuses `inspect_video` and `io/hashing.py`.
- `catalog` (YAML): how a dataset lays out episodes. Only plain `{task_id}`,
  `{episode_id}`, `{camera_id}` placeholders are accepted.

## Guarantees that are tested

- Paths in manifests are relative, normalized POSIX paths; absolute paths,
  `..`, and backslashes are rejected. Machine-specific roots never appear.
- A symlink that resolves outside the data root is rejected.
- Manifests cannot be written inside the data root, including through a symlinked
  output directory; existing outputs and symlink destinations are refused.
- The resolver works on a read-only tree and leaves file listings (size,
  mtime) unchanged.
- Output is deterministic (sorted keys); repeat resolves are equal.
- Every manifest states `exposure_synchronization: unverified` and
  `timestamp_provenance: nominal_frame_index`.

## Known limits

- `frame_count`, `fps`, and sizes come from container metadata via OpenCV;
  PRL does not decode every frame here. A header can disagree with the real
  number of decodable frames.
- A file could change between hashing and inspection (no locking). Run
  `verify` again if a dataset may be changing. This and other open risks are
  tracked in `docs/planning/risk_register.md`.
- `backend` (the OpenCV decoder name) is recorded but not compared by
  `verify`, because it varies with the environment, not the data.
- A matching hash shows the bytes are unchanged, not that the recording is
  correct, synchronized, or calibrated.
- Only the layout of one NORMAN dataset is catalogued. NORMAN's older audit
  paths (`data/raw/blue_tape/...`) are a different layout and are not used.
