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

## Robotics prerequisites by milestone (configuration only, nothing installed for these)

Do each item when its milestone starts, not before. Machine-specific editor settings (for example ROS 2 paths) belong in your personal VS Code user settings, not in the tracked `.vscode/settings.json`.

| Milestone | Before starting, do this | Verify with |
|---|---|---|
| M3 perception | Create a separate GPU env (Python 3.12, PyTorch CUDA wheel, SAM 2.1, DINOv3 loaders); point `PRL_MODEL_ROOT` at the checkpoints | `torch.cuda.is_available()`; `sha256sum` against `model_manifests/` |
| M5 simulation | Obtain a verified SO-101 MJCF/URDF and set `robot_model` in `configs/simulation/so101.yaml` (it is `null` now); keep `allow_hardware_commands: false`; use the `lerobot` env for MuJoCo | Load the model headless; check joint names and limits against the vendor description |
| M5+ ROS 2 | Source `/opt/ros/lyrical/setup.bash` only in the shell that needs it, never in `~/.bashrc`; Python 3.14 only | `ros2 doctor` |
| M6 hardware | Written, supervised procedure with a physical stop; explicit approval per session. No code path commands hardware unattended | Procedure reviewed before first power-on |

Isaac Sim and MoveIt 2 are not installed and stay deferred until a milestone names them.

## Installing tools when a milestone starts

State on 2026-10-25: the `lerobot` conda env has torch 2.11.0+cu128, torchvision, lerobot 0.6.1, mujoco 3.8.1, gymnasium, scipy, pandas, scikit-image and OpenCV. It has no sam2, dinov3, open3d, scikit-learn or matplotlib. MoveIt is not installed. Nothing below has been run yet; each block is a plan to execute at the stated milestone, then record the versions here.

Rules: one environment per row; create new ones under `/mnt/space/adev/envs/` (517 GB free; `/home` has 81 GB); never run `pip install -e` or build inside NORMAN, because that writes into a read-only reference; install upstream projects from a fresh clone at a pinned commit; no system `nvcc` or driver changes are needed for the PyTorch wheels.

**Statistics and analysis (needed for PRL-007).** Add to the PRL core only what the code imports, as an optional extra so `uv.lock` records it:

```bash
uv add --optional analysis scipy pandas matplotlib scikit-learn
uv sync --extra dev --extra analysis && ./scripts/check
```

**GPU perception (M3).**

```bash
uv venv /mnt/space/adev/envs/prl-perception --python 3.12
source /mnt/space/adev/envs/prl-perception/bin/activate
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
git clone https://github.com/facebookresearch/sam2 /mnt/space/adev/third_party/sam2   # then: git checkout <pinned commit>
uv pip install -e /mnt/space/adev/third_party/sam2
uv pip install transformers timm opencv-python-headless scipy
python -c "import torch;print(torch.__version__, torch.cuda.is_available())"
```

DINOv3 is loaded from Meta's official repo or Hugging Face `transformers` using the checkpoint you already hold. Verify the checkpoints with `sha256sum` against `model_manifests/`.

**Robot learning and simulation (M5/M6).** Keep using the `lerobot` env. Add `matplotlib` there only if needed. Verify MuJoCo headless: `python -c "import mujoco; print(mujoco.__version__)"`, then load the verified SO-101 model.

**ROS 2, Gazebo, MoveIt 2 (M5+).** Needs `sudo apt` and is the one step you run yourself, after reading what apt will add: `apt-cache policy ros-lyrical-moveit ros-lyrical-ros-gz`. Source ROS only in the shell that uses it.

**Deferred.** Isaac Sim (heavy, separate Python, 12 GB GPU is marginal). 3D Gaussian splatting needs a CUDA toolkit and a compiler version the toolkit supports (gcc 15 is likely too new); it is not in PRL scope. Open3D and COLMAP when M4 geometry needs them.
