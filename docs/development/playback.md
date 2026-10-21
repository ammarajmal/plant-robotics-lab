# Playback test strategy

Playback tests use short synthetic MP4 recordings and temporary directories.
They validate YAML rejection, source and configuration SHA-256 values,
left/middle/right ordering, output dimensions, contact-sheet creation,
repeat-run deterministic content, missing or mismatched inputs, writer
initialization failure, failure manifests, and CLI exit behavior.

Synthetic `mp4v` is lossy, so tests compare encoded artifact hashes and
structural metadata rather than assuming source pixels survive compression.
The test suite does not establish physical synchronization, target identity,
tracking quality, calibration, or 3D reconstruction.
