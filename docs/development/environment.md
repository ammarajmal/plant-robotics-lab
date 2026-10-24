# PRL development environment

Python 3.12 is the preferred integration baseline because it is the minimum
declared runtime and matches the project's Ruff target. Python 3.14 is also
currently available for compatibility checks.

uv is the canonical dependency manager. Use `uv sync --extra dev` to create or update
the managed environment, `UV_CACHE_DIR=/tmp/prl-uv-cache uv lock --check` in
restricted or read-only-cache environments, and `uv lock --upgrade` only for an
intentional dependency refresh. Reproducible commands use `uv run prl ...` or
the synced environment's `prl` executable. The repository targets Python 3.12;
an existing Python 3.14 environment is not removed or repurposed.

The `.vscode/` directory keeps portable test/editor settings only. ROS paths,
machine-specific interpreter paths, and generated C/C++ browse databases are
excluded from version control. No ROS, CUDA, simulator, or robot dependency is
required for video ingestion.

## Readiness check and quality gate

- `uv run prl doctor` is read-only. It exits 1 if a required item (Python >= 3.12, numpy, cv2, yaml, git, uv) is missing. Optional items (data/model roots, GPU, ROS 2) only warn.
- `./scripts/check` runs the full local gate: lock check, compileall, ruff check, ruff format check, pytest, `git diff --check`, then `prl doctor`. Run it before every commit; CI will run the same commands.
