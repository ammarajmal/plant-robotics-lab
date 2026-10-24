"""Read-only environment checks behind ``prl doctor``."""

from __future__ import annotations

import importlib
import os
import shutil
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

MIN_PYTHON = (3, 12)


@dataclass(frozen=True)
class Check:
    name: str
    required: bool
    ok: bool
    detail: str


def _python() -> Check:
    found = ".".join(str(part) for part in sys.version_info[:3])
    ok = sys.version_info[:2] >= MIN_PYTHON
    return Check("python", True, ok, f"{found} (need >= {'.'.join(map(str, MIN_PYTHON))})")


def _module(name: str, required: bool) -> Check:
    try:
        module = importlib.import_module(name)
    except ImportError as exc:
        return Check(f"import {name}", required, False, f"{type(exc).__name__}: {exc}")
    return Check(f"import {name}", required, True, str(getattr(module, "__version__", "ok")))


def _tool(name: str, required: bool) -> Check:
    path = shutil.which(name)
    return Check(f"tool {name}", required, path is not None, path or "not on PATH")


def _directory_variable(name: str, env: Mapping[str, str]) -> Check:
    value = env.get(name)
    if not value:
        return Check(name, False, False, "unset (needed only for real-data commands)")
    ok = Path(value).is_dir()
    return Check(name, False, ok, value if ok else f"{value} is not a directory")


def run_checks(env: Mapping[str, str] | None = None) -> list[Check]:
    env = os.environ if env is None else env
    return [
        _python(),
        _module("numpy", True),
        _module("cv2", True),
        _module("yaml", True),
        _module("pytest", False),
        _module("ruff", False),
        _tool("git", True),
        _tool("uv", True),
        _directory_variable("PRL_DATA_ROOT", env),
        _directory_variable("PRL_MODEL_ROOT", env),
        _tool("nvidia-smi", False),
        Check("ROS 2 install", False, Path("/opt/ros").is_dir(), "/opt/ros"),
    ]


def report(checks: list[Check], write: Callable[[str], None] = print) -> bool:
    """Print one line per check; return True when every required check passed."""
    for check in checks:
        if check.ok:
            label = "OK  "
        else:
            label = "FAIL" if check.required else "WARN"
        kind = "required" if check.required else "optional"
        write(f"[{label}] {check.name} ({kind}): {check.detail}")
    ready = all(check.ok for check in checks if check.required)
    write("READY: all required checks passed" if ready else "NOT READY: a required check failed")
    return ready
