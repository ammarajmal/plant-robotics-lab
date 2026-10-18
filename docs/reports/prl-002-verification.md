# PRL-002 verification record

Environment:

- Preferred integration interpreter: Python 3.12.13 (`python3.12`)
- Verification interpreter: Python 3.14.4 (`.venv/bin/python`)
- NumPy: 2.5.4
- OpenCV: 5.0.0.93 (`opencv-python-headless`)
- PyYAML: 6.0.3

Commands and observed results:

```text
.venv/bin/python -m pytest -q       -> 11 passed
.venv/bin/ruff check .              -> All checks passed
.venv/bin/ruff format --check .     -> 34 files already formatted
.venv/bin/python -m compileall -q src tests -> exit 0
.venv/bin/prl status                -> PRL foundation and deterministic video ingestion are installed
```

The first Ruff run found three explicit `zip(..., strict=...)` violations and
four formatting differences; those were corrected before the final checks.

Codec limitation: synthetic MP4 fixtures use `mp4v`, which is lossy in this
environment. Tests therefore assert repeatability, shape, dtype, and tolerant
pixel statistics rather than exact encoded pixel values.

Not established by this change: hardware synchronization, exposure timestamps,
cross-camera identity, calibration, 3D reconstruction, tracking success, or
robot capability. No NORMAN files or datasets were modified or copied.
