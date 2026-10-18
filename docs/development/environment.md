# PRL development environment

Python 3.12 is the preferred integration baseline because it is the minimum
declared runtime and matches the project's Ruff target. Python 3.14 is also
currently available for compatibility checks.

The repository has no established lockfile or dependency-manager lock workflow
yet. Dependencies are declared in `pyproject.toml`; a future PRL-003 decision
should select and document one lock strategy before committing a lockfile.

The `.vscode/` directory keeps portable test/editor settings only. ROS paths,
machine-specific interpreter paths, and generated C/C++ browse databases are
excluded from version control. No ROS, CUDA, simulator, or robot dependency is
required for video ingestion.
