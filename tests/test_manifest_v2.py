from __future__ import annotations

from pathlib import Path

import pytest

from llm_adversarial_information_attacks.datasets.experiments import (
    resolve_manifest,
    validate_manifest,
)

SCHEMAS = Path(__file__).parents[1] / "schemas"


def base_manifest() -> dict[str, object]:
    return {
        "schema_version": 2,
        "experiment_id": "pmv2-direct-smoke-v1",
        "dataset": {
            "name": "personamem_v2",
            "revision": "0123456789abcdef",
            "subset": "smoke_v1",
            "events_path": "../subsets/pmv2_smoke/events.jsonl",
            "labels_path": "../labels/pmv2_smoke/labels.jsonl",
            "subset_seed": 20260829,
        },
        "condition": {
            "comparison_regime": "controlled_component",
            "mechanism": "telemem",
            "package_version": "1.10.0",
            "backend": "local",
            "write_policy": "direct",
            "representation": "collection",
            "update_timing": "hot_path",
            "config_ref": "../../configs/memory/telemem.yaml",
        },
        "retrieval": {
            "mode": "native_semantic",
            "candidate_k": 10,
            "returned_k": [1, 3, 5],
            "context_token_budget": 2048,
            "threshold": None,
            "rerank": False,
        },
        "models": {
            "writer": None,
            "responder": {
                "provider": "openai",
                "model": "gpt-4.1-2025-04-14",
                "config_ref": None,
            },
            "embedding": {
                "provider": "openai",
                "model": "text-embedding-3-small",
                "config_ref": None,
            },
            "reranker": None,
        },
        "attack": {
            "overlay_registry": "../../attacks/registry/smoke.yaml",
            "delivery": "direct_api",
            "payload": "preference_inversion",
            "attacker_knowledge": "white_box",
            "attack_set": "pmv2_preference_inversion_v1",
            "budget": {"unit": "record", "value": 1},
            "target_policy": "fixed_before_run",
        },
        "controls": {
            "paired_clean_twin": True,
            "matched_benign_overlay": True,
            "no_memory_baseline": True,
            "full_context_baseline": True,
        },
        "replication": {
            "trial_order_seed": 20260829,
            "option_order_seed": 20260830,
            "generation_replicates": 1,
            "fail_fast": True,
        },
    }


def test_schema_v2_manifest_resolves_to_stable_hash() -> None:
    manifest = base_manifest()
    first = resolve_manifest(manifest, schemas_dir=SCHEMAS)
    second = resolve_manifest(manifest, schemas_dir=SCHEMAS)
    assert first == second
    assert len(first["manifest_hash"]) == 64
    assert validate_manifest(first, schemas_dir=SCHEMAS) == []
    assert "evaluation" not in first


def test_direct_api_rejects_selective_writer_configuration() -> None:
    manifest = base_manifest()
    manifest["condition"]["write_policy"] = "shared_selective"  # type: ignore[index]
    errors = validate_manifest(manifest, schemas_dir=SCHEMAS)
    assert any("direct_api" in error for error in errors)
    assert any("writer model" in error for error in errors)


def test_selective_conversation_requires_writer() -> None:
    manifest = base_manifest()
    manifest["attack"]["delivery"] = "conversation"  # type: ignore[index]
    manifest["attack"]["budget"]["unit"] = "interaction"  # type: ignore[index]
    manifest["condition"]["write_policy"] = "native_selective"  # type: ignore[index]
    with pytest.raises(ValueError, match="writer model"):
        resolve_manifest(manifest, schemas_dir=SCHEMAS)
