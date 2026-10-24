# Safe reuse of NORMAN assets

1. Preserve NORMAN as the reference repository; do not modify it during PRL foundation setup.
2. Verify source licensing, provenance, and confidentiality before copying code or datasets.
3. Inventory candidate modules, their APIs, dependencies, tests, and historical validation.
4. Create a read-only asset manifest with absolute local source path, checksum, ownership status, and destination design.
5. Prefer configurable references to immutable datasets rather than copies.
6. Port a minimal component plus tests in a separate PRL branch; do not silently reimplement experimental logic.
7. Reproduce reference metrics; log differences as new experiments.
8. Do not mix tuned evaluation data with held-out test data.

## Owner declaration (2026-10-25)

The repository owner states that the NORMAN code was written by them and that no code was provided or shared by others. This is the owner's own statement and has not been independently verified. It does not cover (a) third-party code vendored in NORMAN, for example `04_PROJECTS/third_party/GaussianPlant`, (b) model weights and public datasets, whose licences are separate, or (c) any employer or institutional terms that may apply to work done during the internship; check those before publishing or redistributing. Reuse still follows the protocol above: record source path and revision, and copy only code covered by this declaration.
