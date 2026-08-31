from __future__ import annotations

from pathlib import Path

import pytest

from llm_adversarial_information_attacks.datasets.io import write_jsonl
from llm_adversarial_information_attacks.datasets.normalization import normalize_v2
from llm_adversarial_information_attacks.datasets.validation import (
    memory_input,
    validate_records,
)

SCHEMAS = Path(__file__).parents[1] / "schemas"
REVISION = "0123456789abcdef"


def test_v2_normalization_separates_history_query_and_labels(
    v2_source: tuple[Path, Path],
) -> None:
    benchmark, histories = v2_source
    events, labels = normalize_v2(benchmark, histories, source_revision=REVISION)

    assert len(events) == 3
    assert all(event.schema_version == 2 for event in events)
    assert all(event.source_dataset == "personamem_v2" for event in events)
    assert all(event.experimental_topic is None for event in events[:-1])
    assert events[-1].experimental_topic == "food_recommendation"
    assert events[-1].split == "victim_probe"
    assert events[-1].allowed_for_memory is False
    assert labels[0].answer_key == "The quiet cafe"
    assert all("answer_key" not in event.to_dict() for event in events)

    writer_view = memory_input(events[0].to_dict())
    assert "experimental_topic" not in writer_view
    assert "answer_key" not in writer_view
    with pytest.raises(ValueError, match="read-only"):
        memory_input(events[-1].to_dict())


def test_valid_v2_scenario_passes_schema_validation(
    v2_source: tuple[Path, Path],
) -> None:
    benchmark, histories = v2_source
    events, labels = normalize_v2(benchmark, histories, source_revision=REVISION)
    errors = validate_records(
        (event.to_dict() for event in events),
        (label.to_dict() for label in labels),
        schemas_dir=SCHEMAS,
    )
    assert errors == []


def test_serialization_is_byte_identical(
    v2_source: tuple[Path, Path], tmp_path: Path
) -> None:
    benchmark, histories = v2_source
    events, _ = normalize_v2(benchmark, histories, source_revision=REVISION)
    records = [event.to_dict() for event in events]
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    write_jsonl(first, records)
    write_jsonl(second, list(records))
    assert first.read_bytes() == second.read_bytes()


def test_validator_rejects_metadata_leakage_and_mutating_probe(
    v2_source: tuple[Path, Path],
) -> None:
    benchmark, histories = v2_source
    events, labels = normalize_v2(benchmark, histories, source_revision=REVISION)
    records = [event.to_dict() for event in events]
    records[0]["experimental_topic"] = "leaked-query-topic"
    records[-1]["correct_answer"] = "leaked"
    records[-1]["allowed_for_memory"] = True
    errors = validate_records(
        records,
        (label.to_dict() for label in labels),
        schemas_dir=SCHEMAS,
    )
    assert any("evaluation topic leaked" in error for error in errors)
    assert any("label-only fields" in error for error in errors)
    assert any("probes must be read-only" in error for error in errors)


def test_multimodal_history_is_rejected(
    v2_source: tuple[Path, Path],
) -> None:
    benchmark, histories = v2_source
    (histories / "persona-42.json").write_text(
        '[{"role":"user","content":[{"type":"image","url":"x"}]}]',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="text content"):
        normalize_v2(benchmark, histories, source_revision=REVISION)
