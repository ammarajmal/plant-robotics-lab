# Data, model and output storage conventions

| Kind | Where it lives | In Git? | Rule |
|---|---|---|---|
| Raw datasets | `PRL_DATA_ROOT` (currently NORMAN's `datasets/`) | No | Read-only. Described by `data_manifests/*.json`; see [[development/data_sources]]. |
| Model checkpoints | `PRL_MODEL_ROOT` (currently NORMAN's `runtimes/norman-weights/`) | No | Read-only. Fingerprinted by `model_manifests/*.json`. |
| Processed data, experiment outputs | `outputs/`, `artifacts/` (git-ignored) | No | Regenerable; record config and source revision with each result. |
| Caches | `UV_CACHE_DIR`, `.ruff_cache`, `.pytest_cache` | No | Disposable. |
| Evidence summaries | `docs/reports/` | Yes | Historical; never rewritten. |

Nothing is copied out of NORMAN. PRL records where a file is and what its bytes were.

## Checkpoint manifest

`model_manifests/norman_checkpoints.json` holds the size and SHA-256 of three files (DINOv3 ViT-L/16 pretrain, DINOv3 dino.txt head, SAM 2.1 hiera small), computed on 2026-10-25. The SAM 2.1 hash matches the `.sha256` file stored beside it in NORMAN. Verify by hand:

```bash
cd "$PRL_MODEL_ROOT" && sha256sum sam2.1/sam2.1_hiera_small.pt
```

These are local fingerprints. They do not establish upstream origin, version or licence of the weights; that remains open under PRL-005 and PRL-009. Status: implemented (manifest), not validated against upstream.
