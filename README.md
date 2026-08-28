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

Every PersonaMem evaluation row becomes an independent experiment containing the history available at that row's cutoff followed by one read-only evaluation probe. This avoids future-turn leakage and prevents one probe from changing another probe's memory state.

Normalize a local PersonaMem-v1 export:

```shell
uv run python scripts/normalize_personamem.py --version v1 \
  --benchmark path/to/questions_32k.csv \
  --contexts path/to/shared_contexts_32k.jsonl \
  --events-out data/normalized/personamem_v1/events.jsonl \
  --labels-out data/labels/personamem_v1/labels.jsonl
```

For v2, pass the benchmark CSV and a directory containing the downloaded chat-history JSON files:

```shell
uv run python scripts/normalize_personamem.py --version v2 \
  --benchmark path/to/benchmark.csv --contexts path/to/chat_history_32k \
  --events-out data/normalized/personamem_v2/events.jsonl \
  --labels-out data/labels/personamem_v2/labels.jsonl
```

Build the deterministic smoke tier and validate a filled-in manifest:

```shell
uv run python scripts/build_subset.py --events data/normalized/personamem_v1/events.jsonl \
  --labels data/labels/personamem_v1/labels.jsonl --personas 5 --seed 20260828 \
  --events-out data/subsets/pmv1_smoke/events.jsonl \
  --labels-out data/labels/pmv1_smoke/labels.jsonl
uv run python scripts/validate_subset.py data/manifests/my_experiment.yaml
```

The normalizers require local inputs intentionally: downloading is a separate, revision-pinned provenance step. Dataset revisions and model versions belong in the experiment manifest.
