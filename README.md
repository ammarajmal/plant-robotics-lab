# Plant Robotics Lab (PRL)

A research-grade engineering platform for autonomous strawberry plant care and harvesting.

> Status: Initial foundation only. No hardware autonomy or validated 3D tracking is claimed.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
    pytest -q
    ruff check .
    ruff format --check .
    python -m compileall -q src tests
    prl status
```

Read [docs/index.md](docs/index.md) and [docs/planning/roadmap.md](docs/planning/roadmap.md).

The original NORMAN repository is an external reference; raw datasets and weights remain outside Git.
Python 3.12 is the preferred integration baseline. PRL's initial video layer
uses NumPy and headless OpenCV only; it does not claim camera synchronization,
target identity, tracking, or robot capability.
