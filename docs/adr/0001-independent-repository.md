# ADR-0001: Independent Plant Robotics Lab repository

- Date: 2026-10-18
- Status: Accepted; repository created (first commit `5fce0be`, 2026-10-19)

## Context
Existing NORMAN tree contains valuable historical experiments and source code as well as mixed storage, runtimes, documentation, and large datasets.

## Decision
Build an independent `plant-robotics-lab` Python source repository, leaving NORMAN read-only by default. Reference existing datasets in place and port audited reusable components only after ownership and license review.

## Consequences
Clear architecture and learning path; upfront provenance and compatibility effort; no claim that an imported baseline is validated until rerun under PRL.
