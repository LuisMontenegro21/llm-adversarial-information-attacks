"""Validate and deterministically compile immutable attack/control overlays."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jsonschema

from .hashing import sha256_json
from .normalization import synthetic_timestamp, text_blocks


@dataclass(frozen=True, slots=True)
class CompilationResult:
    events: list[dict[str, Any]]
    metadata: dict[str, Any]


def validate_overlay(overlay: dict[str, Any], *, schemas_dir: str | Path) -> list[str]:
    schema = json.loads(
        (Path(schemas_dir) / "overlay.schema.json").read_text(encoding="utf-8")
    )
    validator = jsonschema.Draft202012Validator(schema)
    errors = [error.message for error in validator.iter_errors(overlay)]
    event_count = len(overlay.get("events", []))
    budget = overlay.get("budget", {})
    if budget.get("value") != event_count:
        errors.append("overlay budget value must equal the number of overlay events")
    expected_unit = (
        "record" if overlay.get("delivery") == "direct_api" else "interaction"
    )
    if budget.get("unit") != expected_unit:
        errors.append(
            f"{overlay.get('delivery')} delivery requires {expected_unit!r} budget units"
        )
    if overlay.get("overlay_type") == "clean" and event_count:
        errors.append("clean overlays cannot contain events")
    if overlay.get("overlay_type") != "clean" and not event_count:
        errors.append("non-clean overlays require at least one event")
    return errors


def compile_overlay(
    events: list[dict[str, Any]],
    overlay: dict[str, Any],
    *,
    schemas_dir: str | Path,
) -> CompilationResult:
    errors = validate_overlay(overlay, schemas_dir=schemas_dir)
    if errors:
        raise ValueError("invalid overlay: " + "; ".join(errors))
    if not events:
        raise ValueError("cannot compile an overlay against an empty history")

    history_units = {event.get("history_unit_id") for event in events}
    personas = {event.get("persona_id") for event in events}
    if history_units != {overlay["history_unit_id"]}:
        raise ValueError("overlay history_unit_id does not match the event stream")
    if personas != {overlay["persona_id"]}:
        raise ValueError("overlay persona_id does not match the event stream")

    ordered = sorted(copy.deepcopy(events), key=lambda event: event["sequence"])
    event_ids = [event["event_id"] for event in ordered]
    target_id = overlay["target"]["query_event_id"]
    if target_id not in event_ids:
        raise ValueError(f"overlay target query does not exist: {target_id}")
    target_event = ordered[event_ids.index(target_id)]
    if target_event.get("split") not in {"victim_probe", "unrelated_control_probe"}:
        raise ValueError("overlay target must be a read-only probe")
    anchor = overlay["insert_after_event_id"]
    if anchor is None:
        insertion_index = 0
    else:
        if anchor not in event_ids:
            raise ValueError(f"overlay insertion anchor does not exist: {anchor}")
        insertion_index = event_ids.index(anchor) + 1
        if ordered[insertion_index - 1]["allowed_for_memory"] is False:
            raise ValueError("overlay cannot be inserted after a read-only probe")

    source_revision = ordered[0]["source_revision"]
    split = (
        "attack_insertion"
        if overlay["overlay_type"] == "malicious"
        else "control_insertion"
    )
    inserted: list[dict[str, Any]] = []
    current_turn = 0
    for index, overlay_event in enumerate(overlay["events"]):
        if overlay_event["role"] == "user" or index == 0:
            current_turn += 1
        inserted.append(
            {
                "schema_version": 2,
                "history_unit_id": overlay["history_unit_id"],
                "persona_id": overlay["persona_id"],
                "conversation_id": f"{overlay['overlay_id']}-conversation",
                "turn_id": f"{overlay['overlay_id']}-turn-{current_turn:06d}",
                "event_id": f"{overlay['history_unit_id']}-{overlay_event['overlay_event_id']}",
                "sequence": 0,
                "timestamp": synthetic_timestamp(0),
                "timestamp_is_synthetic": True,
                "role": overlay_event["role"],
                "content": text_blocks(overlay_event["content"]),
                "content_type": "text",
                "source_topic": None,
                "experimental_topic": None,
                "split": split,
                "source_dataset": "personamem_v2",
                "source_revision": source_revision,
                "source_record_id": f"{overlay['overlay_id']}#{index}",
                "source_event_index": index,
                "source_origin": "overlay",
                "allowed_for_memory": True,
                "operation": "message",
                "refers_to_event_id": None,
                "supersedes_event_id": None,
                "overlay_id": overlay["overlay_id"],
                "overlay_event_id": overlay_event["overlay_event_id"],
            }
        )

    inserted_ids = [event["event_id"] for event in inserted]
    if len(inserted_ids) != len(set(inserted_ids)) or set(inserted_ids).intersection(
        event_ids
    ):
        raise ValueError("overlay compilation produced duplicate event IDs")

    compiled = ordered[:insertion_index] + inserted + ordered[insertion_index:]
    for sequence, event in enumerate(compiled):
        event["sequence"] = sequence
        if event.get("timestamp_is_synthetic"):
            event["timestamp"] = synthetic_timestamp(sequence)

    metadata = {
        "schema_version": 2,
        "history_unit_id": overlay["history_unit_id"],
        "overlay_id": overlay["overlay_id"],
        "overlay_hash": sha256_json(overlay),
        "event_order_hash": sha256_json([event["event_id"] for event in compiled]),
        "compiled_events_hash": sha256_json(compiled),
        "event_count": len(compiled),
    }
    return CompilationResult(events=compiled, metadata=metadata)
