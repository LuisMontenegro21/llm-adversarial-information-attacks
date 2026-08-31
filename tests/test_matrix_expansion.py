from __future__ import annotations

from pathlib import Path

import pytest
from test_manifest_v2 import base_manifest

from llm_adversarial_information_attacks.datasets.experiments import expand_matrix

SCHEMAS = Path(__file__).parents[1] / "schemas"


def _matrix() -> dict[str, object]:
    return {
        "schema_version": 2,
        "matrix_id": "pmv2-pi-smoke",
        "base_manifest": base_manifest(),
        "axes": {
            "mechanism": ["telemem", "memanto", "langgraph"],
            "policy": ["direct", "shared_selective", "native_selective"],
            "delivery": ["direct_api", "conversation"],
            "attacker_knowledge": ["black_box", "white_box"],
            "writer_model": [
                "none",
                "openai:gpt-4.1-2025-04-14",
                "example:model-v1",
            ],
        },
        "constraints": [
            {"when": {"delivery": "direct_api"}, "require": {"policy": "direct"}},
            {"when": {"policy": "direct"}, "require": {"writer_model": "none"}},
            {
                "when": {"policy": ["shared_selective", "native_selective"]},
                "forbid": {"writer_model": "none"},
            },
        ],
    }


def test_matrix_expansion_is_deterministic_and_compatible() -> None:
    first = expand_matrix(_matrix(), schemas_dir=SCHEMAS)
    second = expand_matrix(_matrix(), schemas_dir=SCHEMAS)
    assert first == second
    assert len(first) == 36
    assert len({item["manifest_hash"] for item in first}) == 36
    for manifest in first:
        delivery = manifest["attack"]["delivery"]
        policy = manifest["condition"]["write_policy"]
        if delivery == "direct_api":
            assert policy == "direct"


def test_matrix_without_compatibility_constraints_fails() -> None:
    matrix = _matrix()
    matrix["constraints"] = []
    with pytest.raises(ValueError, match="invalid matrix cell"):
        expand_matrix(matrix, schemas_dir=SCHEMAS)
