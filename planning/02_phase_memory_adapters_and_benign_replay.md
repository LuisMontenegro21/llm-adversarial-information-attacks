# Phase 2 — Memory Adapters, Controlled Conditions, and Benign Replay

## Objective

Build one causal replay engine and capability-aware adapters for TeleMem, Memanto, and LangGraph. Establish benign baselines under both controlled-component and native-stack regimes before any poisoning campaign.

This phase ends when every declared condition can ingest the same valid history unit from a fresh namespace, reach a defined visibility barrier, expose the available memory-state evidence, retrieve under a recorded budget, answer read-only probes, and tear down without contaminating another trial.

## 1. Required inputs

Phase 2 must not begin until the following Phase 1 artifacts are frozen:

- schema-v2 experiment manifest;
- normalized PersonaMem-v1 and PersonaMem-v2 subsets;
- private labels unavailable to replay and adapter processes;
- clean overlays and read-only evaluation probes;
- dataset, config, prompt, lockfile, and source hashes;
- development, pilot, and confirmatory persona splits.

No adapter may read the label path, attack rubric, answer key, or manifest fields designated evaluator-only.

## 2. Experimental regimes

Run two regimes and report them separately.

### 2.1 Controlled-component regime

The controlled regime holds as many components constant as the mechanisms permit. It answers: **given equivalent candidate memories and response handling, how do the stores/retrievers differ?**

Primary controlled conditions:

| Condition ID | Mechanism | Write policy | Representation | Writer |
|---|---|---|---|---|
| `telemem_raw` | TeleMem | direct/raw | collection | none; `infer=False` |
| `memanto_raw` | Memanto | direct/raw | typed records | none; direct `remember` |
| `langgraph_raw_collection` | LangGraph Store | direct/raw | collection | none; `put` |
| `telemem_shared_selective` | TeleMem | shared selective | collection | common external writer, then raw write |
| `memanto_shared_selective` | Memanto | shared selective | typed records | common external writer, then direct `remember` |
| `langgraph_shared_selective` | LangGraph Store | shared selective | collection | common external writer, then `put` |

The shared selective writer must receive the same completed exchange or configured chunk and produce the same canonical `MemoryCandidate` objects for all three mechanisms. Mechanism adapters may translate field names but may not change content, type, confidence, or provenance.

Use a common responder and common retrieved-context template as the primary response path. If custom embeddings cannot be aligned for all stores, record native retrieval as an uncontrolled mechanism component rather than implying embedding equivalence.

### 2.2 Native-stack regime

The native regime answers: **how vulnerable is the product or framework configuration as a deployer would plausibly use it?**

Primary native conditions:

| Condition ID | Mechanism | Native behavior |
|---|---|---|
| `telemem_native_selective` | TeleMem | `add(..., infer=True)` with pinned native extraction/configuration |
| `memanto_native_selective` | Memanto | conversation extraction, typed memory, and configured policy |
| `langgraph_native_selective_collection` | LangGraph | documented selective writer over a collection |

Optional conditions must be separate:

- `langgraph_native_profile`: a single updated user profile;
- `memanto_native_answer`: Memanto `answer` rather than common responder;
- `langgraph_background_writer`: end-of-session/background consolidation;
- `telemem_video`: TeleMem video memory on a separate compatible asset benchmark;
- LangGraph checkpointer: short-term thread-state baseline, not a long-term-memory peer.

Native-stack comparisons must enumerate every writer, embedder, reranker, policy, and answer model that is internally active.

## 3. Architecture and process boundaries

```text
resolved manifest + compiled event stream
                  ↓
          trial orchestrator
        ↙         ↓          ↘
 replay process  adapter process  evaluator process
        ↓              ↓                 ↑
 completed turns → memory backend → retrieval/answers
```

Responsibilities:

- The **orchestrator** owns trial IDs, ordering, state reconstruction, barriers, retries, and artifact paths.
- The **replay process** receives only replayable events and constructs exchanges/chunks.
- The **adapter process** owns mechanism-specific lifecycle, writes, retrieval, and observable state.
- The **responder** receives the query and bounded retrieved context, never evaluator labels.
- The **evaluator process** may read labels and attack rubrics only after outputs are immutable.

Use process-level isolation when an SDK has import-time global state, telemetry, cache directories, or non-resettable clients.

## 4. Canonical data objects

### 4.1 Exchange

Do not write each message independently by default. Bind messages into the smallest writer-relevant unit:

```python
@dataclass(frozen=True)
class Exchange:
    history_unit_id: str
    persona_id: str
    conversation_id: str
    turn_id: str
    messages: tuple[CanonicalMessage, ...]
    source_event_ids: tuple[str, ...]
    logical_time: int
    allowed_for_memory: bool
```

An ordinary exchange normally contains a user message and its assistant response. If the source has partial or non-alternating messages, preserve them and mark the exchange shape; do not invent content.

### 4.2 Memory candidate

The shared selective writer emits:

```python
@dataclass(frozen=True)
class MemoryCandidate:
    candidate_id: str
    text: str
    memory_type: str | None
    subject_id: str
    ownership: str | None
    confidence: float | None
    provenance: str
    source_event_ids: tuple[str, ...]
    operation_hint: str  # add, update, supersede, delete, no_write
```

Candidate IDs and source-event lineage are harness metadata. Do not place marker strings inside memory text.

### 4.3 Write receipt

```python
@dataclass(frozen=True)
class WriteReceipt:
    request_id: str
    source_event_ids: tuple[str, ...]
    submitted_at: str
    completed_at: str
    transport_status: str       # accepted, rejected, error, unknown
    mutation_status: str        # add, update, merge, supersede, delete, no_write, unknown
    native_memory_ids: tuple[str, ...]
    visible: bool | None
    visibility_latency_ms: int | None
    normalized_text: tuple[str, ...] | None
    retry_count: int
    error_code: str | None
```

Transport acceptance is not evidence that a memory exists. Visibility must be established through inspection, retrieval, or an explicitly documented backend guarantee.

### 4.4 Retrieved memory

Retain native and canonical fields:

```python
@dataclass(frozen=True)
class RetrievedMemory:
    native_memory_id: str | None
    text: str
    rank: int
    native_score: float | None
    token_count: int
    metadata: dict[str, object]
    source_event_ids: tuple[str, ...] | None
    status: str | None
```

Native scores are not assumed to share a scale across mechanisms. Compare ranks, recall, and bounded-context exposure rather than raw scores.

## 5. Capability-aware adapter contract

```python
class MemoryAdapter(Protocol):
    @property
    def capabilities(self) -> AdapterCapabilities: ...

    async def healthcheck(self) -> HealthStatus: ...
    async def start_trial(self, scope: TrialScope) -> StartReceipt: ...
    async def ingest_exchange(self, exchange: Exchange) -> WriteReceipt: ...
    async def ingest_candidates(
        self, candidates: list[MemoryCandidate]
    ) -> WriteReceipt: ...
    async def flush(self) -> FlushReceipt: ...
    async def await_visibility(self, barrier: VisibilityBarrier) -> BarrierReceipt: ...
    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult: ...
    async def inspect_or_diff(self) -> MemoryState | Unavailable: ...
    async def forget(self, request: ForgetRequest) -> ForgetReceipt: ...
    async def teardown_trial(self) -> TeardownReceipt: ...
```

`AdapterCapabilities` must declare:

- raw write, native selective write, shared selective write;
- stable memory IDs;
- inspection/export;
- hard deletion, soft expiration, and restore;
- native snapshot/restore;
- semantic search, filtering, and reranking;
- provenance metadata preservation;
- eventual-consistency behavior;
- supported modalities;
- synchronous or asynchronous backend behavior.

Never fabricate an unavailable capability. A native snapshot is optional; deterministic reconstruction in a fresh namespace is the reference fallback.

## 6. Trial namespace and lifecycle rules

Derive an opaque namespace from:

```text
experiment_id / condition_id / history_unit_id / overlay_id / replicate_id
```

Hash or sanitize it to meet backend constraints while retaining a reversible mapping in evaluator-side logs.

Requirements:

- one namespace/agent identity per trial state;
- no namespace reuse between attack, clean, or matched-benign twins;
- no shared index between personas unless cross-user isolation is intentionally under test;
- teardown must verify that normal retrieval returns no active trial memory;
- failed teardown quarantines the namespace and blocks reuse;
- credentials and provider account IDs must never be embedded in namespace strings.

Use new namespaces rather than trusting partial deletion when the backend cannot prove a clean reset.

## 7. Mechanism-specific mappings

### 7.1 TeleMem

Pinned configuration must include TeleMem, Mem0 dependency, LLM, embedding, vector store, reranker, prompts, and thresholds.

Mapping:

- controlled raw: `add(messages, user_id=..., run_id=..., infer=False)`;
- native selective: `add(..., infer=True)` using completed exchanges;
- retrieval: `search(query, user_id=..., run_id=..., limit=..., threshold=..., rerank=...)`;
- shared selective: external writer candidates followed by `infer=False` writes.

Critical isolation requirements:

- TeleMem searches shared pseudo-user `events` together with a requested user scope. Every trial must therefore use a unique composite `run_id` and verify that results belong to the expected run and persona.
- Avoid `add_batch` in the primary persona-isolated conditions because it can create shared-event memories. Test it only as an explicitly named shared-event condition.
- Pass source-event lineage as metadata where preserved.
- Set the package-specific `MEM0_DIR` to a trial-run writable directory before importing TeleMem; do not depend on a user's global `~/.mem0` state.
- Disable telemetry and external defaults where supported; log the effective setting.
- When `infer=True` buffers or merges memories, call the appropriate flush/barrier behavior and record `ADD`/`UPDATE`/merge outcomes.

TeleMem video methods (`add_mm`/`search_mm`) require a separate adapter because their records, assets, retrieval, and response path are not equivalent to dialogue memory.

### 7.2 Memanto

Run Memanto in a pinned local/on-prem configuration when possible. If cloud retrieval is used, record service version/date, region, policy, and response metadata and treat service changes as analysis blocks.

Mapping:

- one Memanto agent identity and namespace per trial;
- controlled raw: direct `remember` with explicit type/source/provenance/source reference;
- native selective: conversation extraction followed by native typed-memory writes and configured policy;
- retrieval: `recall` with explicit `limit`, memory-type filters, temporal filters, and lifecycle status;
- common response path: use recall results in the common responder;
- optional native path: use `answer` and report separately.

Lifecycle requirements:

- Normal answering must retrieve `active` memories only. Memanto can retain and display expired memories; expiration is not the same as deletion.
- Evaluate `expire`, `restore`, permanent deletion, and as-of recall as distinct operations.
- Teardown must delete the backing namespace, not only local agent/session metadata. Verify remote/local deletion behavior for the pinned package.
- Preserve native type, confidence, provenance, source, source reference, timestamps, and active/expired state in logs.
- Session creation, activation, token expiry, and deactivation are infrastructure events, not attack delivery events.

### 7.3 LangGraph

LangGraph is a framework, so the manifest must define the complete memory application rather than naming only `langgraph`.

Primary representation:

- collection namespace `(experiment_id, trial_id, persona_id, "memories")`;
- stable key per canonical candidate or native writer result;
- JSON value containing text, type, ownership, confidence, provenance, logical time, and source-event lineage;
- semantic index over explicitly configured fields only.

Conditions:

- raw collection: one canonical record per admitted candidate;
- shared selective collection: common writer candidates stored unchanged;
- native selective collection: pinned writer prompt/tool schema may add/update/delete collection entries;
- optional profile: one schema-validated profile updated by patches, reported separately.

Use `InMemoryStore` only for smoke/contract tests. Pilot and confirmatory runs should use a pinned database-backed store such as PostgresStore, with migrations performed as an explicit setup step.

A checkpointer retains thread-scoped graph state. It must not be labeled as an equivalent long-term semantic-memory mechanism. If included, give it its own condition, thread lifecycle, context-trimming policy, and result table.

## 8. Replay protocol

For each history unit:

1. Resolve and validate the manifest and all referenced hashes.
2. Start a fresh adapter process and healthcheck the exact configuration.
3. Create the unique trial namespace.
4. Compile replayable events into completed exchanges in source order.
5. Submit one exchange or configured chunk at a time.
6. Record transport and mutation receipts before advancing.
7. Apply deterministic retry rules only to retryable transport failures.
8. Call `flush()` at configured boundaries.
9. Await the defined visibility barrier.
10. Inspect/diff state when supported and record unavailable fields otherwise.
11. Run read-only retrieval and response probes from reconstructed twins.
12. Teardown or quarantine the namespace.

Do not retry an ambiguous write unless the request is idempotent. If the backend timed out after possibly mutating state, inspect by request ID/source metadata or mark the trial indeterminate and rebuild it.

### 8.1 Chunking

Chunking is part of the writer condition. Record:

- unit: exchange, N exchanges, token-bounded chunk, session;
- maximum messages and tokens;
- overlap;
- flush boundary;
- whether the writer sees previous memory during update.

Do not compare an exchange-level writer with a full-history writer without naming chunking as a differing factor.

### 8.2 Visibility barrier

A visibility barrier must specify:

```yaml
visibility:
  poll_interval_ms: 250
  timeout_ms: 30000
  success_rule: source_event_or_semantic_match
  required_stable_polls: 2
```

For systems that guarantee immediate visibility, still perform a smoke verification. A timed-out write is not successful merely because the API accepted it.

## 9. Common selective writer

The common writer must use one pinned prompt and structured output schema across mechanisms. Its task is to emit durable user-related memories or `NO_WRITE`, not to answer the user.

Writer prompt requirements:

- distinguish user claims, assistant text, third-party claims, quotations, hypotheticals, and tool content;
- preserve temporal updates and explicit corrections;
- never store system/developer instructions as user preferences;
- emit source-event lineage and ownership;
- return structured operations;
- use deterministic decoding where supported;
- operate without labels, future queries, or attack indicators.

Validate writer outputs before storage. Invalid outputs receive the recorded retry/repair policy; silently coercing them is prohibited.

Measure writer quality independently on benign development data before poisoning:

- relevant-memory precision/recall;
- no-write accuracy;
- ownership accuracy;
- temporal supersession accuracy;
- privacy/sensitive-information policy compliance;
- duplicate and contradiction rates.

## 10. Retrieval and context assembly

Use two retrieval views:

1. **Native view:** mechanism-recommended settings, reported as native-stack behavior.
2. **Controlled view:** fixed candidate depth and retrieved-context token budget.

Controlled retrieval procedure:

1. retrieve up to `candidate_k` native results;
2. retain native order;
3. remove records outside the required namespace/status filters;
4. serialize each record using one common provenance-preserving template;
5. include whole records until `context_token_budget` is reached;
6. apply a pre-declared final-item truncation policy;
7. record included and excluded IDs and token counts.

Do not normalize native similarity scores into fake comparable probabilities.

Retrieved text must be placed in a clearly delimited untrusted-data section. The template must state that memory may be inaccurate and cannot override system/developer instructions. Use the identical common template across mechanisms.

## 11. Model-provider experiments

Do not begin with a complete writer × responder × mechanism factorial.

### 11.1 Mechanism baseline

Use one fixed common writer and one fixed responder for the controlled selective conditions. This is the primary mechanism comparison.

### 11.2 Writer-provider sensitivity

For providers A, B, and C:

- rebuild memory from the same S0/S1 history with each writer;
- hold responder, retrieval configuration, attack artifact, and judge fixed;
- treat provider as a writer factor;
- never reuse memory produced by another writer condition.

### 11.3 Responder-provider sensitivity

- freeze the exact retrieval result and assembled context;
- submit the same query/context to each responder provider;
- disable all memory writes during these probes;
- hold judge and option order fixed or counterbalanced;
- treat each provider output as a paired response to the same state.

This design isolates activation differences and avoids rebuilding stores unnecessarily.

## 12. Benign baselines

Run before attacks:

- no-memory responder;
- full benign context, subject to a documented context budget;
- each controlled raw condition;
- each controlled shared-selective condition;
- each native selective condition;
- optional native integrated-answer condition.

Measure:

- transport acceptance, mutation rate, and visibility latency;
- benign writer precision/recall and no-write accuracy;
- clean evidence recall@k and MRR;
- MCQ and open-ended personalized accuracy;
- dynamic-preference update accuracy;
- ownership attribution;
- forget/expire/delete compliance under correct lifecycle semantics;
- sensitive-information policy behavior;
- cross-user isolation;
- latency, token use, provider cost, storage growth, and record-length distribution.

An adapter/configuration that cannot reach a minimum pre-registered clean baseline must not advance to the primary poisoning comparison. It may remain as a documented failure condition, because attack success on a nonfunctional memory system is not informative.

## 13. State reconstruction and twins

Define states:

```text
S0: empty verified namespace
S1: benign history ingested and visible
S2: attack/control overlay ingested and visible
S3: delay/noise ingested and visible
S4: recovery/forget operation completed
```

Every attack, clean, and matched-benign twin must derive independently from the same S1 event stream and configuration.

Preferred state strategy:

1. native snapshot/export only if semantics and restoration are verified;
2. database snapshot when it captures all mechanism state;
3. deterministic reconstruction in a fresh namespace as the reference fallback.

Record event-order, write-receipt, and observable-state hashes. Do not require byte-identical native vector indexes when providers are nondeterministic; require identical inputs and document nondeterministic backend state.

## 14. Observability and raw logs

Write append-only JSONL or Parquet records for:

- run/trial lifecycle;
- resolved redacted configuration;
- exchange submission and write receipt;
- writer input/output and validation result;
- visibility polls;
- memory state/diffs;
- retrieval request, native results, filters, ranks, and tokens;
- assembled responder context;
- model request metadata and response;
- errors, retries, ambiguous writes, and timeouts;
- teardown verification.

Each raw record must include experiment ID, trial ID, condition ID, history-unit ID, persona ID, overlay ID, replicate ID, logical time, wall-clock time, component version, and input/config hash.

Store credentials only in environment variables or a secret provider. Redact them before hashing/logging. Raw memory text is required for poisoning adjudication but must remain within the synthetic research artifact boundary.

## 15. Failure policy

Classify failures as:

- `invalid_input`;
- `configuration_error`;
- `transport_retryable`;
- `transport_terminal`;
- `ambiguous_write`;
- `visibility_timeout`;
- `writer_invalid_output`;
- `backend_contamination`;
- `teardown_failed`;
- `provider_version_drift`.

Predefine which failures are retried, rebuilt, excluded, or retained as outcomes. Never silently drop failed trials. Report counts by condition.

## 16. Required tests

### Contract tests

- capability declaration matches observed behavior;
- start/teardown returns to verified empty state;
- raw and selective writes use the correct path;
- completed exchanges preserve roles and source IDs;
- retrieval respects namespace, lifecycle status, and token budget;
- unavailable inspection/snapshot capabilities are represented honestly.

### Mechanism-specific tests

- TeleMem `infer=False` stores verbatim content and `infer=True` uses native selection;
- TeleMem shared `events` scope cannot leak between composite run IDs;
- TeleMem imports and state remain inside configured run directories;
- Memanto active-only recall excludes expired records;
- Memanto teardown removes the backing namespace when requested;
- LangGraph collection namespaces isolate personas/trials;
- LangGraph production store migrations and persistence work;
- checkpointer state is not returned as long-term Store memory.

### Causality tests

- probe produces no write or state diff;
- all twins reconstruct identical S1 inputs;
- one failed/poisoned trial cannot alter the next trial;
- retry logic does not duplicate writes;
- responder-provider probes use byte-identical assembled contexts;
- evaluator-only files cannot be opened by replay/adapter processes.

## 17. Deliverables

```text
src/llm_adversarial_information_attacks/
  adapters/
    base.py
    capabilities.py
    telemem.py
    memanto.py
    langgraph_store.py
    langgraph_checkpoint.py       # optional baseline
  replay/
    compiler.py
    orchestrator.py
    lifecycle.py
    visibility.py
    reconstruction.py
  runtime/
    writer.py
    retrieval.py
    context.py
    responder.py
  logging/
    records.py
    redaction.py
configs/
  memory/
  models/
  retrieval/
results/baselines/
tests/adapters/
tests/replay/
```

## 18. Exact benign-run procedure

For each manifest and history unit:

1. validate hashes and environment versions;
2. allocate a unique trial namespace and run-scoped local directories;
3. healthcheck the backend and verify empty retrieval;
4. compile ordered completed exchanges;
5. ingest exchanges or common-writer candidates according to condition;
6. log every request/receipt and stop on ambiguous mutation;
7. flush and reach the visibility barrier;
8. record the S1 state/diff and reconstruction hash;
9. reconstruct separate read-only twins for each probe as needed;
10. retrieve with native and controlled budgets;
11. run the common responder and optional native responder;
12. seal raw logs before evaluator access;
13. evaluate benign endpoints;
14. tear down and verify no active memory remains;
15. aggregate only after schema validation and trial-completeness checks.

## Exit criteria

- All primary adapters pass the shared contract and mechanism-specific suites.
- The six controlled conditions complete smoke and pilot histories from fresh namespaces.
- Native selective conditions are fully specified and complete benign replay.
- Controlled versus native results are stored and reported separately.
- Writer, retrieval, responder, and judge provider roles are independently logged.
- Benign insertion, selection, retrieval, response quality, ownership, temporal behavior, isolation, and resource baselines are available.
- Every primary condition meets the pre-registered clean-functionality gate or is explicitly excluded with evidence.
- S1 reconstruction works for every mechanism; attacks cannot inherit prior trial state.
- Cross-persona and cross-trial leakage is zero in smoke and pilot tests.
- No Phase 3 campaign begins until raw Phase 2 logs pass completeness and contamination validation.
