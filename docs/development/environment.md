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
