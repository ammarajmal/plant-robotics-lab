# Task board

- DONE PRL-001 — Repository foundation, uv lock, Python 3.12 baseline (`5fce0be`, `4931889`, `64eccd7`)
- DONE PRL-002 — Deterministic video ingestion and frame/timestamp contract (`5fc2879`; report: `docs/reports/prl-002-verification.md`). Whether the decoder derives from NORMAN code is not documented.
- DONE PRL-003 — Provenance-aware three-view playback (`67f0acc`; 17 tests passed on 2026-10-21; real NORMAN data not yet played back)
- REVIEW PRL-004 — Read-only NORMAN data-source resolver and portable manifests (branch `feat/prl-004-data-source-resolver`; evidence: `docs/reports/prl-004-verification.md`; one episode only)
- TODO PRL-005 — Audit NORMAN source provenance and code-reuse permissions (licence undecided; no code reused so far)
- TODO PRL-006 — Reproduce and holdout-test Q=10 Kalman result

Renumbered on 2026-10-21 to match Git history. Old IDs: 001→PRL-001, 003+004→PRL-002, 005→PRL-003, 002 (asset manifest part)→PRL-004, 002 (audit part)→PRL-005, 006 unchanged.

Update task states to DOING, REVIEW, DONE only with evidence. Record Git revision and test output when marking DONE.
