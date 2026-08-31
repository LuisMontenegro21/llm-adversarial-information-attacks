from __future__ import annotations

import pytest

from llm_adversarial_information_attacks.datasets.subset import select_personas
from llm_adversarial_information_attacks.datasets.validation import (
    ensure_disjoint_personas,
)


def test_train_and_evaluation_personas_must_be_disjoint() -> None:
    train = [{"persona_id": "pmv2-p1"}, {"persona_id": "pmv2-p2"}]
    evaluation = [{"persona_id": "pmv2-p2"}, {"persona_id": "pmv2-p3"}]
    with pytest.raises(ValueError, match="pmv2-p2"):
        ensure_disjoint_personas(train, evaluation)


def test_stratified_persona_selection_is_deterministic() -> None:
    labels = [
        {"persona_id": "pmv2-p1", "strata": {"preference_type": "static"}},
        {"persona_id": "pmv2-p2", "strata": {"preference_type": "static"}},
        {"persona_id": "pmv2-p3", "strata": {"preference_type": "implicit"}},
        {"persona_id": "pmv2-p4", "strata": {"preference_type": "dynamic"}},
    ]
    first = select_personas(labels, count=3, seed=20260828)
    second = select_personas(reversed(labels), count=3, seed=20260828)
    assert first == second
    assert len(first) == len(set(first)) == 3
