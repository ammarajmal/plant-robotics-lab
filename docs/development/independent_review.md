# Independent review checklist (used to close PRL-006)

A review is independent when the reviewer did not write the code. Close PRL-006 only after the checks below are done and the result is recorded in a new file under `docs/reports/` (do not edit the existing report).

Scope: commits `04fdf3b..899102f` (PR #1). Evidence report: `docs/reports/prl-006-verification.md`.

1. **Reproduce.** On a clean clone: `uv sync --frozen --extra dev && ./scripts/check`. Expect all tests to pass.
2. **Read the diff** (`git diff 04fdf3b 899102f -- src tests`), focusing on `io/decode_audit.py`, `io/resolver.py` and the playback manifest code. Ask: can a hand-edited manifest or a symlink make `verify`, `audit` or playback read a different file than the catalog names?
3. **Check claims against evidence.** For each claim in the report (for example 526/526 frames per camera), find the test or command output that supports it. Anything without support gets labelled unsupported.
4. **Run on real data**, with `PRL_DATA_ROOT` set: `prl data verify --manifest ... --catalog ...` then `prl data audit ...`. Confirm the digests match the report.
5. **Check limits are stated.** Frame counts matching is not camera synchronization. Open risks R-006-1..4 should be honest.
6. **Confirm NORMAN was untouched** (its `git status` and HEAD before and after).
7. **Write the verdict:** approve, or list findings with severity. Then update the task board: REVIEW to DONE only if approved, citing the review file.

An AI reviewer (for example `/codex:rescue` in a fresh session) can do steps 1 to 3 and 5; steps 4 and 6 and the final decision are yours.
