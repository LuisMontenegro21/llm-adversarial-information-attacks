"""Fail-closed schema-v2 validation for PersonaMem-v2 experiment data."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import jsonschema

_LABEL_ONLY_FIELDS = {
    "answer_key",
    "correct_answer",
    "incorrect_answers",
    "all_options",
    "rubric",
    "strata",
}
_PROBE_SPLITS = {"victim_probe", "unrelated_control_probe"}


def validate_records(
    events: Iterable[dict[str, Any]],
    labels: Iterable[dict[str, Any]],
    *,
    schemas_dir: str | Path,
) -> list[str]:
    schema_root = Path(schemas_dir)
    event_validator = jsonschema.Draft202012Validator(
        _load_json(schema_root / "event.schema.json"),
        format_checker=jsonschema.FormatChecker(),
    )
    label_validator = jsonschema.Draft202012Validator(
        _load_json(schema_root / "label.schema.json")
    )
    errors: list[str] = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    event_by_id: dict[str, dict[str, Any]] = {}

    for index, event in enumerate(events):
        errors.extend(
            f"event[{index}]: {error.message}"
            for error in event_validator.iter_errors(event)
        )
        leaked = _LABEL_ONLY_FIELDS.intersection(event)
        if leaked:
            errors.append(
                f"event[{index}]: label-only fields present: {sorted(leaked)}"
            )
        event_id = event.get("event_id")
        if event_id in event_by_id:
            errors.append(f"event[{index}]: duplicate event_id {event_id!r}")
        if isinstance(event_id, str):
            event_by_id[event_id] = event
        grouped[str(event.get("history_unit_id"))].append(event)

    label_event_ids: set[str] = set()
    for index, label in enumerate(labels):
        errors.extend(
            f"label[{index}]: {error.message}"
            for error in label_validator.iter_errors(label)
        )
        event_id = label.get("evaluation_event_id")
        if isinstance(event_id, str):
            label_event_ids.add(event_id)
        event = event_by_id.get(event_id)
        if event is None:
            errors.append(
                f"label[{index}]: evaluation event {event_id!r} does not exist"
            )
        elif event.get("history_unit_id") != label.get("history_unit_id") or event.get(
            "persona_id"
        ) != label.get("persona_id"):
            errors.append(
                f"label[{index}]: label namespace does not match its evaluation event"
            )

    for history_unit_id, scenario in grouped.items():
        sequences = [event.get("sequence") for event in scenario]
        expected = list(range(len(scenario)))
        if sequences != expected:
            errors.append(
                f"history unit {history_unit_id!r}: sequences must be contiguous and ordered from zero"
            )
        personas = {event.get("persona_id") for event in scenario}
        revisions = {event.get("source_revision") for event in scenario}
        if len(personas) != 1:
            errors.append(
                f"history unit {history_unit_id!r}: contains multiple persona namespaces"
            )
        if len(revisions) != 1:
            errors.append(
                f"history unit {history_unit_id!r}: contains multiple source revisions"
            )
        positions = {event.get("event_id"): event.get("sequence") for event in scenario}
        for event in scenario:
            event_id = event.get("event_id")
            split = event.get("split")
            if split in _PROBE_SPLITS and event.get("allowed_for_memory") is not False:
                errors.append(f"event {event_id!r}: probes must be read-only")
            if (
                split == "benign_ingestion"
                and event.get("experimental_topic") is not None
            ):
                errors.append(
                    f"event {event_id!r}: evaluation topic leaked into benign history metadata"
                )
            origin = event.get("source_origin")
            if origin == "dataset" and (
                event.get("overlay_id") is not None
                or event.get("overlay_event_id") is not None
            ):
                errors.append(f"event {event_id!r}: dataset event has overlay metadata")
            if origin == "overlay" and (
                not event.get("overlay_id") or not event.get("overlay_event_id")
            ):
                errors.append(f"event {event_id!r}: overlay lineage is incomplete")
            reference = event.get("refers_to_event_id")
            if event.get("operation") == "forget" and not reference:
                errors.append(
                    f"event {event_id!r}: forget event needs refers_to_event_id"
                )
            for relation in (reference, event.get("supersedes_event_id")):
                if relation and (
                    relation not in positions
                    or positions[relation] >= event.get("sequence", -1)
                ):
                    errors.append(
                        f"event {event_id!r}: relation {relation!r} must point backward in the same history unit"
                    )

    for event_id, event in event_by_id.items():
        if event.get("split") in _PROBE_SPLITS and event_id not in label_event_ids:
            errors.append(
                f"event {event_id!r}: evaluation probe has no answer key or rubric"
            )
    return errors


def memory_input(event: dict[str, Any]) -> dict[str, Any]:
    """Return only fields permitted to reach a memory writer."""
    if not event.get("allowed_for_memory"):
        raise ValueError(f"event {event.get('event_id')!r} is read-only")
    return {
        "event_id": event["event_id"],
        "persona_id": event["persona_id"],
        "conversation_id": event["conversation_id"],
        "turn_id": event["turn_id"],
        "role": event["role"],
        "content": event["content"],
        "operation": event["operation"],
        "source_record_id": event["source_record_id"],
    }


def ensure_disjoint_personas(
    train_events: Iterable[dict[str, Any]], evaluation_events: Iterable[dict[str, Any]]
) -> None:
    train = {event["persona_id"] for event in train_events}
    evaluation = {event["persona_id"] for event in evaluation_events}
    overlap = sorted(train.intersection(evaluation))
    if overlap:
        raise ValueError(f"train and evaluation personas overlap: {overlap}")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
