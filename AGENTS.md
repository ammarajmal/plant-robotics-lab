# AGENTS.md

This file is the single source of agent instructions for this repository. Claude Code, Codex, opencode and other coding agents all read it (`CLAUDE.md` only imports it). Do not duplicate these rules elsewhere.

## Sources of truth

Code, tests, committed configuration, and the canonical docs (`docs/architecture/`, `docs/development/`) are authoritative. Roadmap, task board, experiment protocols, and report templates live in `docs/`; do not duplicate them here. Agent memory (for example claude-mem) is optional supplemental session context, never a source of truth: verify anything it says against the repo.

## Commands

uv is the canonical dependency manager (Python >=3.12, hatchling build).

```bash
uv sync --extra dev                                  # pytest/ruff live in the optional-dependencies `dev` extra
uv run pytest -q
uv run pytest tests/test_playback.py::test_cli_success_and_missing_config_failure -q   # single test
uv run ruff check .
uv run ruff format --check .
uv run python -m compileall -q src tests
uv run prl status
uv run prl data resolve --catalog configs/data/norman_catalog.yaml --task-id T --episode-id E --output PATH   # needs PRL_DATA_ROOT or --data-root
uv run prl data verify --manifest PATH     # exit 0 match, 1 drift, 2 error
uv run prl playback three-view --config configs/playback/three_view.yaml [--output-dir DIR]
UV_CACHE_DIR=/tmp/prl-uv-cache uv lock --check    # read-only-cache environments
```

Ruff: line length 100, rules E4/E7/E9/F/I/B/UP. Also run `git diff --check` before committing. Conventional commits (`feat(io): ...`), one focused change per branch (`feat/ fix/ test/ docs/ chore/`). Stage explicit files; never `git add .`.

## Architecture

Intended pipeline (`docs/architecture/system_overview.md`): ingestion -> perception -> target tracker -> geometry -> planning -> guarded execution -> verification. Only ingestion and playback exist; `perception/ tracking/ geometry/ robotics/ simulation/ policies/ evaluation/` are empty placeholder packages.

- `domain/`: plain dataclasses/enums, independent of ROS, LeRobot, camera SDKs, PyTorch, simulators. Put adapters at system boundaries.
- `io/video.py`: OpenCV-only decoding (`inspect_video`, `read_frame`, `iter_three_view`). Raises `ThreeViewAlignmentError`/`FrameDecodeError` on unequal frame count, size, or FPS instead of truncating or substituting frames. Views are strictly ordered `left_arm, middle, right_arm`.
- `playback/`: `config.py` (strict YAML validation to frozen `PlaybackConfig`; relative paths resolve against the config file), `render.py` (side-by-side MP4 + contact sheet), `provenance.py` (manifest: SHA-256s, git revision, versions). Kept separate so each is testable alone.
- `io/resolver.py` + `domain/datasets.py` (PRL-004): read-only resolution of dataset episodes into portable manifests (`data_manifests/`) with root-relative paths; never copies or writes under the data root, rejects symlinks escaping it. See `docs/development/data_sources.md`.
- `cli.py`: `prl` entry point; config/playback errors exit with code 2.

### Failure-manifest guarantee (and its limits)

`render_three_view` writes `manifest.json` from a `finally` block after the stream/render stage starts, with `status: "failed"` and the error string when any `Exception` occurs, then raises `PlaybackError` with only the last error message (original exception type is lost). It does NOT cover:
- config failures (`load_config` runs earlier: bad YAML, wrong view order, missing config file) - no manifest is written;
- failure of `output_dir.mkdir` (before the `try`) or of writing/building the manifest itself;
- partial artifacts: a failed run can leave a partial `three_view.mp4`/`contact_sheet.jpg` that the failed manifest does not list or hash, and `streams` may be empty or incomplete.

Treat a failed manifest as evidence of the failure, not as a complete record of what is on disk.

## Invariants (do not weaken)

- Frame alignment is nominal frame-index only (`TimestampProvenance.NOMINAL_FRAME_INDEX`; config `hardware_synchronization_verified: false`). Never claim camera synchronization, target identity, tracking, calibration, or 3D capability in code, docs, or output labels.
- Safety: a missing, ambiguous, or unverified physical target must never trigger an autonomous manipulation command. A visible target is not sufficient: workspace limits, collision checks, operator interlock, force/contact limits, and e-stop are separate requirements.
- Raw datasets, recordings, and model weights stay out of Git. `PRL_DATA_ROOT`/`PRL_MODEL_ROOT` in `.env.example` are workstation-local examples.

## Scientific evidence policy

Label every capability as exactly one of: proposed, implemented, tested, validated, deployed. Code existing is "implemented"; passing automated tests is "tested"; "validated" needs evidence on real data/hardware; "deployed" needs a supervised run. Never invent experiment outcomes, metrics, or dataset results, and never state that tests, lint, or commands passed unless you ran them in this session and saw the output. Report failures and skipped checks verbatim.

## Agent safety policy

- Run `git status` before making changes; do not clobber unrelated uncommitted work.
- NORMAN (`/mnt/space/adev/projects/active/norman`) is a read-only external reference: never modify it, and do not copy proprietary or unlicensed code from it.
- Preserve raw data and historical evidence (existing reports, manifests, `docs/reports/`); do not delete, move, or overwrite them.
- Do not push, force-push, reset --hard, rebase published history, or otherwise perform destructive Git operations without explicit authorization.
- Never operate physical robot hardware (or write code paths that do so unattended) without explicit approval, supervision, and a physical stop procedure. Do not reinstall or alter GPU/ROS environments.

## Learning rule

For significant changes, briefly explain: the engineering concept involved, the design rationale, how it was validated, and a suggested next learning objective.

## Testing notes

Tests synthesize tiny `mp4v` videos under `tmp_path`. `mp4v` is lossy, so assert on structural metadata and encoded-artifact hashes, not source pixels. Determinism checks use `deterministic_manifest()` (strips `created_utc`, `run_id`, `git.dirty`, `execution.errors`). See `docs/development/playback.md`.
