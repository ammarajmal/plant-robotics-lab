# Task board

- DONE PRL-001 — Repository foundation, uv lock, Python 3.12 baseline (`5fce0be`, `4931889`, `64eccd7`)
- DONE PRL-002 — Deterministic video ingestion and frame/timestamp contract (`5fc2879`; report: `docs/reports/prl-002-verification.md`). Whether the decoder derives from NORMAN code is not documented.
- DONE PRL-003 — Provenance-aware three-view playback (`67f0acc`; 17 tests passed on 2026-10-21; real NORMAN data not yet played back)
- DONE PRL-004 — Read-only NORMAN data-source resolver and portable manifests (merged `04fdf3b`; `docs/reports/prl-004-verification.md`; one episode only)
- TODO PRL-005 — Audit NORMAN source provenance and code-reuse permissions (licence undecided; no code reused so far)
- REVIEW PRL-006 — Real-data playback and source integrity (branch `feat/prl-006-real-data-playback`; evidence: `docs/reports/prl-006-verification.md`; awaiting independent review; closes R-004-3)
- TODO PRL-007 — Reproduce and holdout-test Q=10 Kalman result (renumbered from PRL-006 on 2026-10-21)
- TODO PRL-008 — Hardlink-free manifest publication fallback for filesystems without `os.link` (deferred from PRL-004 review; see R-004-7)

Renumbered on 2026-10-21 to match Git history; the Kalman holdout task moved from PRL-006 to PRL-007 when PRL-006 was assigned to real-data playback. Old IDs: 001→PRL-001, 003+004→PRL-002, 005→PRL-003, 002 (asset manifest part)→PRL-004, 002 (audit part)→PRL-005, 006 unchanged.

Update task states to DOING, REVIEW, DONE only with evidence. Record Git revision and test output when marking DONE.
