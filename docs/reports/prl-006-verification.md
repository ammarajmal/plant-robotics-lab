# PRL-006 verification record: real-data playback and source integrity

Branch `feat/prl-006-real-data-playback` (not merged; awaiting independent review).
Status label for every capability below: **tested** (automated tests) and, for the
`episode_00000` run, **observed** on real data. Nothing here is "validated" or
"deployed".

Environment: Python 3.12.13, NumPy 2.5.4, OpenCV 5.0.0 (FFMPEG backend; avcodec
62.28.101, avformat 62.12.101, avutil 60.26.101), Linux 7.0.0-38-generic x86_64.

## Automated checks (run 2026-10-21)

```text
pytest -q                           -> 122 passed   (baseline 91)
ruff check .                        -> all checks passed
ruff format --check .               -> 53 files already formatted
compileall -q src tests             -> exit 0
uv lock --check                     -> Resolved 11 packages (lock current)
git diff --check main..HEAD         -> exit 0
prl data verify --catalog (real)    -> manifest matches current files: sizes, hashes, metadata, exit 0
```

New tests cover: identity mismatches (dataset, root variable, task, episode,
camera swap, other-episode path, wrong extension case, foreign layout), in-root
symlinks to another camera or episode, symlinked directories, exit code 2 for
identity errors; decode-audit header over- and under-claims, mid-stream decoder
exception, wrong shape/dtype, unreadable media, timing summary, determinism,
drift refusal, output placement and exit codes; manifest-driven playback.

## Source integrity (episode_00000, `leaf_removal_point_blue`)

Inputs were selected only from `data_manifests/norman_leaf_removal_point_blue_episode_00000.json`
after binding it to `configs/data/norman_catalog.yaml`. Encoded-file SHA-256 values equal
those in the manifest and in NORMAN's own audit CSV (see PRL-004 report).

## Full sequential decode audit

Artifact: `artifacts/audit/prl006_episode00000_decode_audit.json` (Git-ignored).

| Camera | Metadata frames | Decoded frames | Match | Anomalies | Stream digest (first 16) |
|---|---|---|---|---|---|
| left_arm | 526 | 526 | yes | none | `1fc1f6248a73f1b8` |
| middle | 526 | 526 | yes | none | `3de796cac27a6875` |
| right_arm | 526 | 526 | yes | none | `f838052c2f0fe69e` |

All frames were 640x480 uint8 BGR. Episode digest (chain of the three stream digests):
`78202fee136c474a82c2b2e10f1b3e5a1f9dcd217d36cbadf406093f07948a68`. A second run
produced identical deterministic fields (everything except `created_utc`,
`elapsed_s`, `git.dirty`). Decoded counts now agree with container metadata and
with NORMAN's own decoded count (526); PRL's own decode is the independent check.

Decoder-reported `CAP_PROP_POS_MSEC`: first 0.0 ms, last 17500.0 ms, constant step
33.333 ms, no non-increasing steps, identical across cameras. This equals
`frame_index / 30` and therefore adds no information beyond the container's
constant frame rate. It is **not** exposure time and says nothing about camera
synchronization.

## Playback artifacts (Git-ignored)

`artifacts/playback/prl006_episode00000/`

| File | SHA-256 |
|---|---|
| `three_view.mp4` (1920x480, 30 fps, 526 frames) | `73f4ce1ae28fdb4433449c9b54b560d782b1d498a873f583bea8d8daf051c7f3` |
| `contact_sheet.jpg` | `09ca4949408a198463761f929d0084bad3a65ed46e7798446ae000c4f880bad6` |
| `manifest.json` | records source-manifest SHA-256 `0b4f2bb5…fe3ad`, data-root-relative sources, git revision, runtime |

Each tile is labelled with its camera and `source frame N`, plus `ALIGNMENT NOMINAL ONLY`
(checked by eye on the contact sheet). Re-rendering produced byte-identical MP4 and JPEG
files under this environment.

## NORMAN and data safety

NORMAN's full `git status --porcelain=v2 --branch -uall` output, `HEAD`
(`0c3f81a`, branch `dev-blue-tape-benchmarks`) and `git diff` hash were identical
before and after (NORMAN was already dirty before this task). The three source
files kept the same sizes, modification times and SHA-256. No file under NORMAN was
newer than the pre-run baseline. The recordings are user-writable (`rw-rw-r--`),
so read-only handling rests on code discipline (risk R-006-3).

## Not established

Camera exposure synchronization, frame-timestamp accuracy, calibration,
cross-view identity, tracking, 3D geometry, licence/reuse permission for NORMAN
code, other episodes, and decoded-pixel equality in any other decoder
environment.

## Concepts

1. **Container frame count vs decoded frame count.** `CAP_PROP_FRAME_COUNT` is a
   header field, sometimes estimated from duration times fps. The decoded count is
   how many frames the decoder actually returned. They can differ after truncation
   or muxing errors, so PRL counts by decoding and treats a mismatch, or an early end
   of stream, as an explicit finding.
2. **Why source identity matters.** A hash proves bytes are unchanged, not that they are
   the intended bytes. A manifest that points `middle` at `left_arm`'s file, or at
   another episode, still verifies against itself. Binding every path to the
   catalog's expected location, and rejecting symlinks, makes "this is
   episode_00000 / middle" a checked fact.
3. **What a presentation timestamp represents.** A PTS says when a decoder should
   present a frame relative to the stream's clock. It is a property of the encoded
   file, not of when light reached the sensor. A regular PTS grid is what you get
   from a constant-frame-rate muxer, whatever the cameras did.
4. **How frame-content hashes help.** Hashing dtype, shape, channel order and
   pixel bytes lets later runs detect any change in what the decoder produces
   (different library, different file) without storing frames. It is a different
   object from the MP4 checksum, and only comparable under the same decoder build.
5. **Why three-view playback is not tracking.** Playing three streams side by side
   pairs frames by index. It establishes no common clock, no shared coordinate system
   and no identity link between a leaf in one camera and the same leaf in another.
   Cross-view tracking needs calibration, verified synchronization and an
   association method.
