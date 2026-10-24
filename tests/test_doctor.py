from __future__ import annotations

from pathlib import Path

import pytest

from plant_robotics.cli import main
from plant_robotics.doctor import Check, report, run_checks


def test_optional_failures_do_not_block_readiness() -> None:
    lines: list[str] = []
    checks = [Check("a", True, True, "ok"), Check("b", False, False, "missing")]
    assert report(checks, lines.append) is True
    assert lines[1].startswith("[WARN] b (optional)")
    assert lines[-1].startswith("READY")


def test_required_failure_blocks_readiness() -> None:
    lines: list[str] = []
    assert report([Check("a", True, False, "boom")], lines.append) is False
    assert lines[0].startswith("[FAIL] a (required)")
    assert lines[-1].startswith("NOT READY")


def test_data_root_variable_is_checked_from_given_env(tmp_path: Path) -> None:
    checks = {c.name: c for c in run_checks({"PRL_DATA_ROOT": str(tmp_path)})}
    assert checks["PRL_DATA_ROOT"].ok
    assert not checks["PRL_MODEL_ROOT"].ok
    assert not checks["PRL_MODEL_ROOT"].required


def test_cli_doctor_runs_in_dev_environment(capsys: pytest.CaptureFixture[str]) -> None:
    main(["doctor"])
    assert "READY" in capsys.readouterr().out
