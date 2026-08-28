from __future__ import annotations

import csv
import json
from pathlib import Path

from llm_adversarial_information_attacks.datasets.io import write_jsonl
from llm_adversarial_information_attacks.datasets.normalization import normalize_v1
from llm_adversarial_information_attacks.datasets.validation import validate_records


def _v1_fixture(tmp_path: Path) -> tuple[Path, Path]:
    contexts = tmp_path / "contexts.jsonl"
    contexts.write_text(
        json.dumps(
            {
                "shared_context_id": "history-1",
                "context": [
                    {"role": "user", "content": "I prefer quiet restaurants."},
                    {"role": "assistant", "content": "I'll remember that."},
                    {"role": "user", "content": "This turn is in the future."},
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    questions = tmp_path / "questions.csv"
    with questions.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "persona_id",
                "question_id",
                "question_type",
                "topic",
                "user_question_or_message",
                "correct_answer",
                "all_options",
                "shared_context_id",
                "end_index_in_shared_context",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "persona_id": "42",
                "question_id": "q-1",
                "question_type": "latest_preference",
                "topic": "food",
                "user_question_or_message": "Where should I eat?",
                "correct_answer": "The quiet cafe",
                "all_options": "['The quiet cafe', 'The stadium bar']",
                "shared_context_id": "history-1",
                "end_index_in_shared_context": "2",
            }
        )
    return questions, contexts


def test_normalization_keeps_labels_and_future_events_out_of_replay(
    tmp_path: Path,
) -> None:
    questions, contexts = _v1_fixture(tmp_path)
    events, labels = normalize_v1(questions, contexts)

    assert [event.content for event in events[:-1]] == [
        "I prefer quiet restaurants.",
        "I'll remember that.",
    ]
    assert events[-1].split == "victim_probe"
    assert events[-1].allowed_for_memory is False
    assert all("correct_answer" not in event.to_dict() for event in events)
    assert labels[0].answer_key == "The quiet cafe"


def test_valid_normalized_scenario_passes_schema_validation(tmp_path: Path) -> None:
    questions, contexts = _v1_fixture(tmp_path)
    events, labels = normalize_v1(questions, contexts)
    errors = validate_records(
        (event.to_dict() for event in events),
        (label.to_dict() for label in labels),
        schemas_dir=Path(__file__).parents[1] / "schemas",
    )
    assert errors == []


def test_serialization_is_byte_identical(tmp_path: Path) -> None:
    questions, contexts = _v1_fixture(tmp_path)
    events, _ = normalize_v1(questions, contexts)
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    records = [event.to_dict() for event in events]
    write_jsonl(first, records)
    write_jsonl(second, reversed(list(reversed(records))))
    assert first.read_bytes() == second.read_bytes()


def test_validator_rejects_label_leakage_and_mutating_probe(tmp_path: Path) -> None:
    questions, contexts = _v1_fixture(tmp_path)
    events, labels = normalize_v1(questions, contexts)
    records = [event.to_dict() for event in events]
    records[-1]["correct_answer"] = "leaked"
    records[-1]["allowed_for_memory"] = True
    errors = validate_records(
        records,
        (label.to_dict() for label in labels),
        schemas_dir=Path(__file__).parents[1] / "schemas",
    )
    assert any("label-only fields" in error for error in errors)
    assert any("probes must be read-only" in error for error in errors)
