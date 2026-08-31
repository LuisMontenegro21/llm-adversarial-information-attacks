# llm-adversarial-information-attacks
This repository contains the proof of work for adversarial information attacks towards AI Agents based on Large Language Models.

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then synchronize the locked environment:

```shell
uv sync
```

## Phase 1: dataset curation

Phase 1 uses two physically separate streams:

- replayable event JSONL under `data/normalized/` or `data/subsets/`;
- private answer labels under `data/labels/`, which must never be passed to a memory adapter.

Every PersonaMem-v2 evaluation row becomes an independent schema-v2 history unit containing its text history followed by one read-only evaluation probe. History events retain source provenance without receiving evaluation-query topics.

Normalize a pinned local PersonaMem-v2 text export:

```powershell
uv run python scripts/normalize_personamem.py `
  --benchmark path/to/benchmark.csv --histories path/to/chat_history_32k `
  --revision <immutable-dataset-revision> `
  --events-out data/normalized/personamem_v2/events.jsonl `
  --labels-out data/labels/personamem_v2/labels.jsonl
```

Build the deterministic smoke tier and validate a filled-in manifest:

```powershell
uv run python scripts/build_subset.py --events data/normalized/personamem_v2/events.jsonl `
  --labels data/labels/personamem_v2/labels.jsonl --personas 5 --seed 20260829 `
  --events-out data/subsets/pmv2_smoke/events.jsonl `
  --labels-out data/labels/pmv2_smoke/labels.jsonl
uv run python scripts/validate_subset.py data/manifests/my_experiment.yaml
```

Compile one premade overlay without modifying the normalized source:

```powershell
uv run python scripts/compile_overlay.py `
  --events data/subsets/pmv2_smoke/events.jsonl `
  --overlay data/overlays/my_attack.yaml `
  --events-out data/compiled/my_attack/events.jsonl `
  --metadata-out data/compiled/my_attack/metadata.json
```

Resolve one run manifest or expand a comparison matrix:

```powershell
uv run python scripts/resolve_experiment.py data/manifests/my_experiment.yaml `
  --out data/manifests/resolved/my_experiment.yaml
uv run python scripts/expand_matrix.py `
  configs/experiments/pmv2_preference_inversion_matrix.yaml `
  --out-dir data/manifests/resolved/matrix
```

The normalizer requires local inputs intentionally: downloading is a separate, revision-pinned provenance step. Dataset revisions, attack-set versions, and immutable model identifiers belong in the experiment manifest.
