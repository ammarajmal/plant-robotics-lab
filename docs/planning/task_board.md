# Task board

- DONE PRL-001 — Repository foundation, uv lock, Python 3.12 baseline (`5fce0be`, `4931889`, `64eccd7`)
- DONE PRL-002 — Deterministic video ingestion and frame/timestamp contract (`5fc2879`; report: `docs/reports/prl-002-verification.md`). Whether the decoder derives from NORMAN code is not documented.
- DONE PRL-003 — Provenance-aware three-view playback (`67f0acc`; 17 tests passed on 2026-10-21; real NORMAN data not yet played back)
- DONE PRL-004 — Read-only NORMAN data-source resolver and portable manifests (merged `04fdf3b`; `docs/reports/prl-004-verification.md`; one episode only)
- TODO PRL-005 — Audit NORMAN source provenance and code-reuse permissions (owner declaration recorded 2026-10-25, see `docs/development/migration_and_provenance.md`; third-party code and weights are the owner's downloads and still need upstream licence entries; no code reused so far)
- REVIEW PRL-006 — Real-data playback and source integrity (branch `feat/prl-006-real-data-playback`; evidence: `docs/reports/prl-006-verification.md`; merged to `main` in PR #1 on 2026-10-24; independent review not confirmed, so not DONE; closes R-004-3)
- PAUSED PRL-007 — B0/B1 baselines ported (PR #10) and reproduce NORMAN's `left_arm` numbers (B0 0.47 px, B1 Q=1 15.39 px, Q=10 4.88 px full-visibility error; 30 frames, in-sample). Holdout on `middle`/`right_arm` NOT evaluable (2026-10-25): labels were made but the HSV detector found no blob near them (colour at labels H≈48-63, outside the blue range; the visible tape in those views appears teal-green, unconfirmed). No Q=10 generalisation claim. Resume with a detector that is valid per view, or confirm the target marker
- TODO PRL-008 — Hardlink-free manifest publication fallback for filesystems without `os.link` (deferred from PRL-004 review; see R-004-7)
- TODO PRL-009 — Off-disk backup of the data and model roots; record upstream origin and licence of the SAM 2.1 and DINOv3 checkpoints (local SHA-256s done in `model_manifests/`)
- TODO PRL-010 — Decide whether to add a type checker and pre-commit hooks; decide GitHub plan or visibility for branch protection

Renumbered on 2026-10-21 to match Git history; the Kalman holdout task moved from PRL-006 to PRL-007 when PRL-006 was assigned to real-data playback. Old IDs: 001→PRL-001, 003+004→PRL-002, 005→PRL-003, 002 (asset manifest part)→PRL-004, 002 (audit part)→PRL-005, 006 unchanged.

Update task states to DOING, REVIEW, DONE only with evidence. Record Git revision and test output when marking DONE.
