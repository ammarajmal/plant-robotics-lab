# Plant Robotics Lab (PRL)

A research-grade engineering platform for autonomous strawberry plant care and harvesting.

> Status: Initial foundation only. No hardware autonomy or validated 3D tracking is claimed.

## Quick start

```bash
uv sync --dev
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run python -m compileall -q src tests
uv run prl status
```

Headless nominal three-view evidence can be generated with
`prl playback three-view --config configs/playback/three_view.yaml`. The
configuration must name all three source files; playback fails on missing,
corrupt, or structurally incompatible streams and writes a provenance manifest.

Read [docs/index.md](docs/index.md) and [docs/planning/roadmap.md](docs/planning/roadmap.md).

The original NORMAN repository is an external reference; raw datasets and weights remain outside Git.
Python 3.12 is the preferred integration baseline. PRL's initial video layer
uses NumPy and headless OpenCV only; it does not claim camera synchronization,
target identity, tracking, or robot capability.
