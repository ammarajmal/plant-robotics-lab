# Safe reuse of NORMAN assets

1. Preserve NORMAN as the reference repository; do not modify it during PRL foundation setup.
2. Verify source licensing, provenance, and confidentiality before copying code or datasets.
3. Inventory candidate modules, their APIs, dependencies, tests, and historical validation.
4. Create a read-only asset manifest with absolute local source path, checksum, ownership status, and destination design.
5. Prefer configurable references to immutable datasets rather than copies.
6. Port a minimal component plus tests in a separate PRL branch; do not silently reimplement experimental logic.
7. Reproduce reference metrics; log differences as new experiments.
8. Do not mix tuned evaluation data with held-out test data.

## Owner declaration (2026-10-25, updated)

The repository owner states that (a) the NORMAN code was written by them; (b) the third-party code under NORMAN's `04_PROJECTS/third_party/` (`sam2`, `Grounded-SAM-2`, `gaussian-splatting`, `GaussianPlant`) was downloaded by them from its upstream projects; (c) the SAM 2.1 and DINOv3 weights were downloaded by them through their own accounts from Meta's distribution. Nothing was provided or shared by NORMAN's employer or others. These are the owner's own statements and are not independently verified.

Consequences: (a) permits reuse of the owner's own code. (b) and (c) are third-party works governed by their upstream licences, not by this declaration. Before redistributing or publishing, record each upstream licence and the download source (PRL-009); the DINOv3 and SAM 2.1 terms in particular must be read from Meta's pages, not assumed. PRL-005 stays open until those entries exist. Employer or institutional terms from the internship are also unchecked. Prefer fresh upstream clones over copying from NORMAN.
