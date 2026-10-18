# Coding agent handoff — Foundation audit and Gate 1

Repository: `/mnt/space/adev/projects/active/plant-robotics-lab`
Reference only: `/mnt/space/adev/projects/active/norman`

## Goal
Audit the new scaffold, confirm Git and package status, identify reusable deterministic video decoder in NORMAN, and propose minimal integration to PRL without changing NORMAN.

## Guardrails
- Inspect and report before modifying anything.
- Do not delete, move, reset, reinstall GPU/ROS environments or copy raw datasets.
- Preserve existing decoder semantics and timestamp provenance.
- Do not claim three-camera physical synchronization.
- No robot hardware actions.

## Deliverable
Provenance note, API map, minimal proposed diff, tests and exact commands, blockers, and next acceptance gate. Stop before copying proprietary or unlicensed code.
