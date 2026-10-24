# Risk register

Open risks that are known, accepted for now, and not yet fixed. Add an entry
rather than silently carrying a limitation in someone's head. Status values:
`open`, `mitigated`, `closed`.

## PRL-004 data-source resolver

Raised by the independent review of `feat/prl-004-data-source-resolver`.

| ID | Risk | Impact | Current mitigation | Possible fix | Status |
|---|---|---|---|---|---|
| R-004-1 | TOCTOU: `resolve`/`verify` check containment, then `stat`, hash, and `inspect_video` each reopen the path (`io/resolver.py`, `_locate`/`_observe`/`verify_episode`). A file replaced between steps can yield a manifest whose size, hash, and metadata describe different bytes. | A manifest could misdescribe the file; evidence, not safety, is affected. | Documented; rerun `verify`; hashes detect later change. | Record `os.stat` before and after hashing/inspection and fail on size or `mtime_ns` change; or open once (`O_NOFOLLOW`) and hash/`fstat` the descriptor. | open |
| R-004-2 | Symlink retargeting: a symlink inside the data root that passes the containment check can be retargeted before it is opened. | Read of a file outside the root, or of another episode. Read-only; nothing is written. | Containment check at resolve time; size/hash catch later change within a file. | Same single-open approach as R-004-1. | partly mitigated (PRL-006): redirection is rejected at check time; retargeting between check and open remains |
| R-004-3 | No manifest-to-catalog identity binding: `verify` does not check that `relative_path` matches `task_id`, `episode_id`, `camera_id` or the catalog layout, and an in-root symlink to another episode's file is accepted. | A hand-edited or mislinked manifest can verify successfully against the wrong file. | Hash and size compare against the manifest's own recorded values. | Re-derive paths from the catalog during `verify` (or store and check a layout hash); optionally refuse in-root symlinks. | mitigated (PRL-006): `verify --catalog`, `audit` and manifest-driven playback bind identity and reject every symlink component; plain `verify` without `--catalog` remains unbound |
| R-004-4 | Duplicate YAML keys in a catalog are accepted (`yaml.safe_load` keeps the last value). | A catalog can silently shadow `dataset_id` or `layout`. | None beyond key-set validation. | Use a loader subclass that raises on duplicate keys. | open |
| R-004-5 | `verify` reads the environment variable named by the manifest's `root_variable`. | A hand-edited manifest selects which variable is used as the data root; read-only. | Value must be a readable directory; identifier-validated. | Take the variable only from the catalog or an allowlist. | open |
| R-004-6 | `frame_count`/`fps` are container metadata, not decoded counts. | A header can disagree with decodable frames. | Documented in `docs/development/data_sources.md` and the verification report. | A separate full-decode audit (not part of PRL-004). | mitigated for `episode_00000` (PRL-006 full decode: 526/526 frames per camera); other episodes unaudited |
| R-004-7 | `resolve`/`audit` publish without `--force` via `os.link`, which some filesystems (FAT/exFAT, some network/FUSE mounts) do not support. | Manifest cannot be written there without `--force`; fails closed (exit 2). | None. | Fall back to an `O_EXCL` create. Tracked as PRL-008. | open (deferred) |

## PRL-006 real-data playback and source integrity

| ID | Risk | Impact | Current mitigation | Possible fix | Status |
|---|---|---|---|---|---|
| R-006-1 | `CAP_PROP_POS_MSEC` is OpenCV/FFmpeg decoder-reported presentation time. On `episode_00000` it equals `frame_index / 30` to about 1e-11 ms for all cameras, so it adds nothing beyond the constant-frame-rate container clock. | Misreading it as exposure time would be a false synchronization claim. | Labelled "not exposure time" in every audit and manifest; `exposure_synchronization: unverified`. | Hardware timestamps or a measured sync event (M4). | open |
| R-006-2 | Frame-content hashes depend on the decoder build (OpenCV 5.0.0, avcodec 62.28.101). | Another environment may decode different pixels from the same file and produce different digests. | Runtime and library versions recorded in the audit; encoded MP4 SHA-256 recorded separately. | Compare digests when the environment changes; pin the build in CI. | open |
| R-006-3 | The source recordings are mode `rw-rw-r--` and owned by the user. | Read-only handling is by code discipline, not by the operating system. | Code opens sources read-only; NORMAN status/HEAD/diff hash compared before and after. | Make the originals read-only or mount read-only. | open |
| R-006-4 | Audit verifies sources, then decodes them in a separate open (same gap as R-004-1). | A file changed between steps would be audited under stale verification. | Encoded hash is re-checked per run; digests are reproducible. | Single-open design (R-004-1). | open |

Closed after review: uncaught exceptions exiting 1 (now 2), silent manifest
overwrite and non-atomic write, and the output-before-hash ordering.
