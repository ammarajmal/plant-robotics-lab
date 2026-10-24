# PRL roadmap

## M0 — Repository foundation
- [ ] Create separate Git repository and verify package installation
- [ ] Run scaffold unit tests; record versions
- [ ] Decide licenses and NORMAN source reuse permissions
- [ ] Establish data and model asset manifest (data: `episode_00000` only, PRL-004 merged; models: not started)

## M1 — Multi-camera input
- [x] Audit existing deterministic decoder
- [x] Compose reproducible three-view playback (PRL-003)
- [x] Emit timestamp provenance and frame manifest (PRL-003)
- [x] Create failure and mismatch tests (PRL-003)
- [x] Play back real `episode_00000` from a catalog-bound manifest with a full decode audit (PRL-006, merged in PR #1; independent review not confirmed)

## M2 — Persistent 2D tracking
- [ ] Reproduce B0/B1/B2 reference results
- [ ] Evaluate Q=10 independently; quantify occlusion failures
- [ ] Validate identity persistence and lost-target behavior

## M3 — Plant organ understanding
- [ ] Define organ labels and annotation standards
- [ ] Create old-leaf / runner / ripe-fruit baselines
- [ ] Compare SAM 2.1 and DINOv3 feature methods

## M4 — Multi-view geometry
- [ ] Intrinsics and extrinsics with reprojection tests
- [ ] Timestamp and synchronization provenance
- [ ] 3D localization and uncertainty

## M5 — SO-101 simulation
- [ ] Verify authentic robot model and joint semantics
- [ ] Implement MuJoCo reach-and-grasp scene
- [ ] Test safe simulated task execution

## M6 — Robot hardware and learning
- [ ] Safe teleoperation and logging
- [ ] Calibrated robot-camera transforms
- [ ] Pilot demonstrations and ACT baseline
- [ ] Closed-loop supervised manipulation

## M7 — Professional dual-arm system
- [ ] Verify actual arm specifications and control interfaces
- [ ] Design task coordination and collision constraints
- [ ] Transfer perception, tracking and learned policies
- [ ] Evaluate on unseen plants and report safety, reliability and throughput

## M8 — Research and release
- [ ] Document ablations and uncertainty
- [ ] Freeze public-safe datasets and code release
- [ ] Manuscript and deployment documentation
