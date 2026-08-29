# Phase 1 — Dataset Curation, Threat Model, and Experiment Specification

## Objective

Create immutable, replayable PersonaMem-v1 and PersonaMem-v2 experiment units and a versioned experiment specification that can drive TeleMem, Memanto, and LangGraph without exposing future events or evaluator-only information.

Phase 1 is already substantially implemented in this repository. The additional work described under **Schema-v2 compatibility gate** is required before Phase 2 because provider roles, write policies, memory representations, attack overlays, and event-level provenance cannot be represented faithfully by the current schema.

This phase ends when a third party can reconstruct the exact ordered inputs to any trial from committed code, a pinned dataset revision, a manifest, and private label/attack artifacts—without relying on mutable application state.

## 1. Normative language and research boundary

The words **must**, **should**, and **may** are normative:

- **must**: required for a valid experiment;
- **should**: required unless a documented exception is recorded;
- **may**: optional extension that must be labeled if used.

The harness is restricted to synthetic personas, isolated services, and inert outputs. It must not be connected to production assistants, real user memories, shared tenant accounts, real credentials, or tools capable of external side effects.

The experiment evaluates durable-memory integrity. Same-turn prompt injection that never reaches durable memory is outside the primary estimand and must be labeled separately if measured.

## 2. System-under-test decomposition

Do not define the system under test only by a product name. Every condition must identify the following components:

```text
event stream
  → memory writer / selection policy
  → memory representation and update policy
  → backing store and retriever
  → retrieved-context assembler
  → response model
  → evaluator
```

The canonical condition tuple is:

```text
(dataset, history unit, writer, representation, store/retriever,
 retrieval policy, responder, attack delivery, attack payload, defense)
```

This prevents a provider-specific writer, embedder, reranker, or responder from being mistaken for an effect of TeleMem, Memanto, or LangGraph.

Use the following vocabulary consistently:

| Term | Meaning | Examples |
|---|---|---|
| Mechanism | Memory product or implementation | TeleMem, Memanto, LangGraph Store |
| Write policy | How content is admitted to memory | direct/raw, shared selective, native selective |
| Representation | Shape of durable memory | document collection, profile, native typed records |
| Update timing | When memory formation occurs | hot path, end-of-session/background |
| Modality | Sensory/data form | text, image, audio, video |
| Response path | How memory affects an answer | common responder, native integrated answer |

Direct versus selective storage is a **write-policy** distinction, not a modality distinction.

## 3. Threat model

Each attack must declare one delivery capability and one payload strategy. Delivery describes how the content reaches the memory system; payload describes what the content attempts to corrupt.

### 3.1 Delivery capabilities

| Delivery capability | Attacker access | Valid interpretation |
|---|---|---|
| `direct_api` | Can call a privileged memory-write API | White-box upper bound; compromised ingestion path |
| `conversation` | Can send ordinary chat inputs; native writer decides what persists | Query-only or account-session attacker |
| `indirect_content` | Controls text/image/document/tool content observed during a legitimate interaction | Third-party or retrieved-content attacker |
| `cross_user` | Writes as principal A and targets principal B | Namespace/tenant isolation test |

### 3.2 Payload strategies

The primary payload strategies are:

1. `preference_inversion`: inserts or strengthens a false preference that contradicts the current ground truth;
2. `retrieval_bridge`: increases the probability that attacker-aligned content is retrieved for a pre-registered victim query and activated by the responder;
3. `ownership_confusion`: causes third-party, quoted, hypothetical, or tool-provided content to be attributed to the user.

Cross-user contamination is a mandatory isolation experiment. It must not be pooled with same-user behavioral ASR.

### 3.3 Attacker knowledge

Record attacker knowledge independently from access:

- `black_box`: sees only public inputs and outputs;
- `gray_box`: knows mechanism family and query class but not stored records or embeddings;
- `white_box`: knows configuration, retrieved records, or embedding model;
- `privileged`: can directly write or modify memory.

The attacker must not use evaluation labels, clean control outcomes, or future victim responses during attack construction.

## 4. Research questions and pre-registered estimands

Primary research questions:

1. Does attacker-controlled content reach the memory-write interface?
2. Does the writer create, update, merge, supersede, or delete a durable record because of that content?
3. Does an attacker-aligned memory remain visible after consolidation and benign delay events?
4. Is contaminated memory retrieved for the pre-registered victim query?
5. Does retrieval cause a paired change toward the attacker goal relative to a clean twin?
6. Does the effect generalize across memory mechanisms, write policies, datasets, and response providers?
7. What benign utility, privacy, ownership, and isolation costs accompany the attack or defense?

Before running a campaign, designate one primary target-query endpoint, one primary memory-state endpoint, one primary retrieval endpoint, one clean-utility endpoint, and the planned primary contrasts. All other analyses must be labeled secondary or exploratory.

## 5. Dataset roles

Use the datasets as separate strata, not as one pooled benchmark:

- **PersonaMem-v1:** explicit preferences, preference evolution, long-distance recall, and engineering of causal replay.
- **PersonaMem-v2:** implicit preference inference, ownership, hypothetical or noisy statements, dynamic preferences, privacy-sensitive attributes, and long histories.

PersonaMem-v2 contains scenarios labeled as multimodal, but this must not automatically be treated as equivalent to a mechanism's native video or image memory. TeleMem's video pipeline, for example, is a distinct video-to-frames-to-captions path. A modality experiment requires compatible source assets, an asset manifest, and a separate adapter contract. Otherwise, the primary benchmark remains text/transcript memory and any multimodal evaluation is reported as an auxiliary study.

## 6. Canonical experiment unit

One benchmark question must become one independent **history unit**:

```text
history available at the question cutoff
  → optional attack overlay
  → optional delay/noise overlay
  → one or more read-only probes
```

No probe may alter the memory state used by another probe. Use a snapshot when supported or reconstruct the pre-probe state in a fresh namespace by deterministic replay.

The history unit identifier must be stable across mechanisms and providers. A trial identifier is derived later by adding mechanism, model, attack, defense, and replicate dimensions.

## 7. Canonical event schema

Schema v2 must preserve raw source provenance and distinguish turns, sessions, assets, and experimental overlays:

```json
{
  "schema_version": 2,
  "history_unit_id": "pmv2-q-000017",
  "persona_id": "pmv2-p0042",
  "conversation_id": "conv-0007",
  "turn_id": "turn-0043",
  "event_id": "pmv2-q-000017-e000043",
  "sequence": 43,
  "timestamp": "2026-01-08T10:00:00Z",
  "role": "user",
  "content": [{"type": "text", "text": "..."}],
  "content_type": "text",
  "source_topic": null,
  "experimental_topic": "food_recommendation",
  "split": "benign_ingestion",
  "source_dataset": "personamem_v2",
  "source_revision": "<immutable-commit>",
  "source_record_id": "<original-row-id>",
  "source_event_index": 43,
  "allowed_for_memory": true,
  "operation": "message"
}
```

Requirements:

- `source_topic` must contain only event-level source metadata. If the source has no per-event topic, use `null` or `unknown`; do not copy the evaluation query topic onto every history event.
- `experimental_topic` may contain evaluator-side stratification metadata but must not be passed to the writer, retriever, or responder unless explicitly part of the condition.
- `source_record_id` must identify the original event or history object when available. The evaluation row ID may be stored separately as `history_unit_id`.
- `turn_id` must bind user and assistant messages that form one exchange.
- Content assets must use immutable local references plus SHA-256 hashes. Remote mutable URLs are not sufficient for replay.
- Synthetic timestamps must be labeled as synthetic. Temporal experiments must use event sequence as the authoritative ordering unless original timestamps are available.

### 7.1 Evaluator-only labels

Labels must remain in a physically separate stream. A label may contain:

```json
{
  "history_unit_id": "pmv2-q-000017",
  "persona_id": "pmv2-p0042",
  "evaluation_event_id": "pmv2-q-000017-eval",
  "answer_key": "...",
  "incorrect_answers": ["..."],
  "rubric": "...",
  "preference_type": "dynamic_implicit",
  "ownership": "user",
  "sensitivity": "non_sensitive"
}
```

The memory path must never receive answer keys, rubrics, MCQ distractors during memory formation, preference/ownership ground-truth annotations, future events, attack success labels, or clean-twin outcomes.

MCQ choices may be introduced only by the evaluation-input builder at the read-only probe. Option order must be deterministic from a recorded seed or counterbalanced across conditions.

## 8. Attack overlays

Do not mutate the immutable normalized dataset to insert attacks. Store a separate overlay:

```yaml
overlay_id: pmv2-q-000017-attack-a1
history_unit_id: pmv2-q-000017
insert_after_event_id: pmv2-q-000017-e000043
events:
  - overlay_event_id: a1-e1
    role: user
    template_id: preference_inversion_v1
    private_parameters_ref: ../../private_attack_params/a1.json
delay_schedule:
  source_event_ids: [e000044, e000045, e000046]
```

The overlay compiler must verify the insertion anchor, preserve original source ordering, assign deterministic composite positions, keep the attack classification evaluator-only, and compute an event-order hash.

Clean and matched-benign overlays must use the same number of events, role pattern, approximate length, topic, and delay schedule.

## 9. Subset construction

Create three scales:

| Tier | Personas | Purpose | Statistical interpretation |
|---|---:|---|---|
| Smoke | 3–5 per dataset | Contract, schema, and isolation debugging | No scientific claims |
| Pilot | At least 20 per dataset, expanded as feasible | Variance and power estimation; condition screening | Preliminary only |
| Confirmatory | Determined by power analysis | Pre-registered primary comparisons | Final claims |

Sampling must occur at persona level and be deterministic. Stratify on available dimensions such as static/dynamic preference, explicit/implicit evidence, user/third-party ownership, stereotypical/neutral/anti-stereotypical preference, sensitivity, history-token bin, and scenario family.

Queries from the same persona are correlated. Selecting more questions from the same persona does not replace selecting more personas.

Maintain disjoint persona sets for attack/prompt development, detector calibration, pilot evaluation, and confirmatory evaluation.

## 10. Temporal layout

Each compiled scenario follows:

```text
benign warm-up
  → read-only pre-attack probes from a twin state
  → attack or control overlay
  → writer flush/visibility barrier
  → benign delay/noise
  → retrieval-only probes
  → response probes
  → optional recovery/forget probes
```

Do not impose percentage windows when they destroy a benchmark question's true cutoff. Prefer explicit event anchors and fixed delay counts. Record both event distance and token distance from attack insertion to victim probe.

## 11. Experiment manifest schema v2

The manifest must describe every component capable of changing the result:

```yaml
schema_version: 2
experiment_id: pmv2_controlled_selective_pilot_v1

dataset:
  name: personamem_v2
  revision: <full-immutable-revision>
  subset: pilot_v1
  events_path: ../subsets/pmv2_pilot/events.jsonl
  labels_path: ../labels/pmv2_pilot/labels.jsonl
  assets_manifest: null
  subset_seed: 20260828

condition:
  comparison_regime: controlled_component  # or native_stack
  mechanism: telemem
  package_version: 1.10.0
  backend: local
  write_policy: shared_selective
  representation: collection
  update_timing: hot_path
  config_ref: ../../configs/memory/telemem_controlled.yaml

retrieval:
  mode: native_semantic
  candidate_k: 10
  returned_k: [1, 3, 5, 10]
  context_token_budget: 2048
  threshold: null
  rerank: true

models:
  writer:
    provider: <provider>
    model: <immutable-model-id>
    config_ref: ../../configs/models/writer.yaml
  responder:
    provider: <provider>
    model: <immutable-model-id>
    config_ref: ../../configs/models/responder.yaml
  embedding:
    provider: <provider-or-native>
    model: <immutable-model-id-or-native>
  reranker:
    provider: <provider-or-native>
    model: <immutable-model-id-or-native>
  judge:
    provider: <provider>
    model: <immutable-model-id>
    config_ref: ../../configs/judges/default.yaml

attack:
  overlay_registry: ../../attacks/registry/pilot.yaml
  delivery: conversation
  payload: retrieval_bridge
  budget: {unit: interaction, value: 3}
  target_policy: fixed_before_run

controls:
  paired_clean_twin: true
  matched_benign_overlay: true
  no_memory_baseline: true
  full_context_baseline: true

replication:
  trial_order_seed: 20260828
  option_order_seed: 20260829
  generation_replicates: 5
  fail_fast: true
```

### 11.1 Model configuration requirements

For each model role record:

- provider and exact model identifier returned by the API;
- request date and provider response metadata;
- system/developer/user prompt hashes;
- temperature, top-p, maximum output tokens, seed if honored, and reasoning mode;
- retry policy and timeout;
- SDK and API-version headers when available;
- input/output token counts and cost basis.

If the provider silently aliases a model, the returned identifier and execution date define a separate analysis block.

The attack generator is not a runtime model role. Attack artifacts must be generated and frozen before evaluation, with their generator metadata recorded in the attack registry.

## 12. Schema-v2 compatibility gate

Before Phase 2, update the implemented schema and normalizers without discarding Phase 1's existing label isolation and cutoff logic:

1. add history-unit, conversation, and turn identifiers;
2. split source metadata from experimental stratification metadata;
3. preserve per-event source provenance instead of copying evaluation-row metadata;
4. add overlay and asset schemas;
5. expand the manifest to model writer, responder, embedding, reranker, and judge separately;
6. add comparison regime, write policy, representation, timing, retrieval budget, controls, and replication settings;
7. retain a migration reader for schema-v1 smoke fixtures or regenerate them deterministically.

## 13. Reproducibility hashes

Compute and retain normalized-event, private-label, asset-manifest, compiled event-order, resolved-manifest, prompt-template, attack-registry, rubric, lockfile, and source-commit hashes. Record the dirty-tree flag.

Do not hash secrets. Configuration resolution must redact credentials before serialization.

## 14. Validation requirements

The validator must fail closed when:

- event, turn, or history-unit IDs are duplicated;
- events are not strictly ordered;
- a relation points forward or outside its history unit;
- source and experimental metadata are conflated;
- a label-only field appears in replayable data;
- future events appear before the benchmark cutoff;
- a probe is writable or MCQ options appear during memory formation;
- a forget event precedes its target or supersession is topologically invalid;
- persona splits overlap;
- attack/control overlays differ outside declared matched fields;
- an asset is missing or has the wrong hash;
- a supposedly read-only probe changes memory state;
- a manifest omits a runtime model role;
- an unpinned dataset, package, prompt, or model alias is used in a confirmatory run.

## 15. Required tests

- Normalization excludes future turns and labels.
- Source provenance survives normalization.
- Evaluation topics are not copied into history metadata.
- History compilation plus overlay is deterministic.
- Option ordering is deterministic and probe-only.
- Asset hashes are verified.
- Personas remain disjoint across development and evaluation splits.
- Every probe is read-only.
- Replay and label interfaces are physically separate.
- Manifest v2 rejects missing writer/responder/judge roles.
- The same inputs generate byte-identical compiled streams.

## 16. Deliverables

```text
data/
  manifests/
  normalized/
  subsets/
  overlays/
  labels/                    # evaluator-only
  assets/                    # optional, hash-pinned
schemas/
  event.schema.json
  label.schema.json
  overlay.schema.json
  experiment.schema.json
scripts/
  normalize_personamem.py
  build_subset.py
  compile_overlay.py
  validate_subset.py
tests/
  test_dataset_causality.py
  test_persona_isolation.py
  test_overlay_compilation.py
  test_manifest_v2.py
```

## 17. Exact replication procedure

An independent operator must be able to:

1. check out the recorded source commit;
2. install the exact lockfile environment;
3. obtain the dataset at the recorded immutable revision;
4. normalize it using the recorded command and inputs;
5. verify raw-input and normalized-output hashes;
6. rebuild the subset using the recorded persona-selection seed;
7. compile each clean, benign-control, and attack overlay;
8. validate every stream and private label file;
9. compare generated hashes with the manifest;
10. proceed to Phase 2 without exposing evaluator-only content to replay code.

## Exit criteria

- Schema v2 represents every mechanism, write policy, representation, retrieval configuration, model role, attack, and control used later.
- Smoke and pilot subsets validate without errors.
- Rebuilding produces byte-identical event and overlay ordering.
- Labels, attack goals, and future events are inaccessible from replay and adapter code.
- Event-level provenance is preserved; query metadata is not assigned to unrelated history events.
- Every primary target has a clean twin, matched-benign overlay, unrelated control query, and pre-registered rubric.
- Dataset licenses, attribution, immutable revisions, and intended research use are recorded.
- No Phase 2 run starts until manifest, dataset, overlay, and lockfile hashes are frozen.
