# Safe reuse of NORMAN assets

1. Preserve NORMAN as the reference repository; do not modify it during PRL foundation setup.
2. Verify source licensing, provenance, and confidentiality before copying code or datasets.
3. Inventory candidate modules, their APIs, dependencies, tests, and historical validation.
4. Create a read-only asset manifest with absolute local source path, checksum, ownership status, and destination design.
5. Prefer configurable references to immutable datasets rather than copies.
6. Port a minimal component plus tests in a separate PRL branch; do not silently reimplement experimental logic.
7. Reproduce reference metrics; log differences as new experiments.
8. Do not mix tuned evaluation data with held-out test data.
