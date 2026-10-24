# Experiment index

One row per recorded run. Generated outputs live in Git-ignored `artifacts/`; the
digests below let a later run be compared without committing media.

| ID | Date | Task | Inputs | Command | Outputs | Result |
|---|---|---|---|---|---|---|
| PRL-006-A | 2026-10-21 | Full decode audit, `episode_00000` | `data_manifests/norman_leaf_removal_point_blue_episode_00000.json` + `configs/data/norman_catalog.yaml` | `prl data audit --manifest … --catalog … --output artifacts/audit/prl006_episode00000_decode_audit.json` | audit JSON | 526/526 frames x3 cameras; episode digest `78202fee…07948a68` |
| PRL-006-B | 2026-10-21 | Three-view playback | `configs/playback/norman_leaf_removal_point_blue_episode_00000.yaml` | `prl playback three-view --config …` | `artifacts/playback/prl006_episode00000/` | success; MP4 sha `73f4ce1a…c7f3`; re-render byte-identical |

Report: `docs/reports/prl-006-verification.md`. Environment: OpenCV 5.0.0, Python 3.12.13.
