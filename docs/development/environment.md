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

## Environment architecture and compatibility

Do not install everything into one Python environment. Each row is a separate environment with its own interpreter. Status words follow the evidence policy in `AGENTS.md`; "import-tested" means only that `import` succeeded on 2026-10-25, not that the library was exercised.

| Environment | Purpose | Interpreter | Evidence on this workstation | Needed |
|---|---|---|---|---|
| PRL core (`.venv`, from `uv.lock`) | Ingestion, playback, manifests, CLI | CPython 3.12.13 (uv-managed) | tested: 126 tests, gate passes in CI and in a clean clone | now |
| GPU perception | PyTorch, SAM 2.1, DINOv3 | to be decided at M3 | not installed; NORMAN holds the weights (see `data_sources.md`) | M3 |
| Robot learning (`miniforge3/envs/lerobot`) | LeRobot, MuJoCo | CPython 3.12.14 | import-tested: torch 2.11.0+cu128 (CUDA available), lerobot 0.6.1, mujoco 3.8.1 | M5/M6 |
| ROS 2 (`/opt/ros/lyrical`) | Robot middleware | system Python 3.14 | installed, not sourced or run | M5+ |
| Simulation extras | Gazebo, MoveIt 2, Isaac Sim | n/a | Gazebo vendor packages present; MoveIt and Isaac not found | later |

Why separate: ROS 2 here uses Python 3.14 while PRL core is 3.12, and PyTorch/CUDA pins would constrain the core's lockfile. Connect environments through files, manifests or messages, never by sharing site-packages.

GPU: driver 595.99.02 (reports CUDA 13.2). There is no system `nvcc`; PyTorch wheels bundle their own CUDA runtime, so none is needed.

## Onboarding and recovery

Resume after a break:

```bash
cd /mnt/space/adev/projects/active/plant-robotics-lab
git switch main && git pull --ff-only
git status                # expect a clean tree
uv sync --extra dev
./scripts/check           # must end with QUALITY GATE PASSED
```

New workstation: install `git`, `uv` and the GitHub CLI; `gh auth login`; `git clone https://github.com/ammarajmal/plant-robotics-lab.git`; run the block above. Then set `PRL_DATA_ROOT` (see `.env.example` and `data_sources.md`) and run `uv run prl doctor`. Raw data, recordings and model weights are not in Git and must be restored separately.

What is and is not backed up: committed work is on `origin` once pushed (private GitHub repository; `main` is not branch-protected on this plan, so a green CI check is a rule you follow, not one GitHub enforces). Unpushed branches, `.venv`, caches and everything under the data and model roots exist only on this disk. A disk-level backup of the data root is an open task on the task board.
