# Risk register

Open risks that are known, accepted for now, and not yet fixed. Add an entry
rather than silently carrying a limitation in someone's head. Status values:
`open`, `mitigated`, `closed`.

## PRL-004 data-source resolver

Raised by the independent review of `feat/prl-004-data-source-resolver`.

| ID | Risk | Impact | Current mitigation | Possible fix | Status |
|---|---|---|---|---|---|
| R-004-1 | TOCTOU: `resolve`/`verify` check containment, then `stat`, hash, and `inspect_video` each reopen the path (`io/resolver.py`, `_locate`/`_observe`/`verify_episode`). A file replaced between steps can yield a manifest whose size, hash, and metadata describe different bytes. | A manifest could misdescribe the file; evidence, not safety, is affected. | Documented; rerun `verify`; hashes detect later change. | Record `os.stat` before and after hashing/inspection and fail on size or `mtime_ns` change; or open once (`O_NOFOLLOW`) and hash/`fstat` the descriptor. | open |
| R-004-2 | Symlink retargeting: a symlink inside the data root that passes the containment check can be retargeted before it is opened. | Read of a file outside the root, or of another episode. Read-only; nothing is written. | Containment check at resolve time; size/hash catch later change within a file. | Same single-open approach as R-004-1. | open |
| R-004-3 | No manifest-to-catalog identity binding: `verify` does not check that `relative_path` matches `task_id`, `episode_id`, `camera_id` or the catalog layout, and an in-root symlink to another episode's file is accepted. | A hand-edited or mislinked manifest can verify successfully against the wrong file. | Hash and size compare against the manifest's own recorded values. | Re-derive paths from the catalog during `verify` (or store and check a layout hash); optionally refuse in-root symlinks. | open |
| R-004-4 | Duplicate YAML keys in a catalog are accepted (`yaml.safe_load` keeps the last value). | A catalog can silently shadow `dataset_id` or `layout`. | None beyond key-set validation. | Use a loader subclass that raises on duplicate keys. | open |
| R-004-5 | `verify` reads the environment variable named by the manifest's `root_variable`. | A hand-edited manifest selects which variable is used as the data root; read-only. | Value must be a readable directory; identifier-validated. | Take the variable only from the catalog or an allowlist. | open |
| R-004-6 | `frame_count`/`fps` are container metadata, not decoded counts. | A header can disagree with decodable frames. | Documented in `docs/development/data_sources.md` and the verification report. | A separate full-decode audit (not part of PRL-004). | open |

Closed after review: uncaught exceptions exiting 1 (now 2), silent manifest
overwrite and non-atomic write, and the output-before-hash ordering.
