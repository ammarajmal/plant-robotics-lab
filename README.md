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
prl status
```

Read [docs/index.md](docs/index.md) and [docs/planning/roadmap.md](docs/planning/roadmap.md).

The original NORMAN repository is an external reference; raw datasets and weights remain outside Git.
