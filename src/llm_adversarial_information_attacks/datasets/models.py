"""Canonical schema-v2 records for PersonaMem-v2 experiment histories."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Role = Literal["user", "assistant", "system", "tool"]
EventSplit = Literal[
    "benign_ingestion",
    "control_insertion",
    "attack_insertion",
    "delay_noise",
    "victim_probe",
    "unrelated_control_probe",
]
SourceOrigin = Literal["dataset", "overlay"]


@dataclass(frozen=True, slots=True)
class Event:
    schema_version: Literal[2]
    history_unit_id: str
    persona_id: str
    conversation_id: str
    turn_id: str
    event_id: str
    sequence: int
    timestamp: str
    timestamp_is_synthetic: bool
    role: Role
    content: list[dict[str, Any]]
    content_type: Literal["text"]
    source_topic: str | None
    experimental_topic: str | None
    split: EventSplit
    source_dataset: Literal["personamem_v2"]
    source_revision: str
    source_record_id: str
    source_event_index: int
    source_origin: SourceOrigin
    allowed_for_memory: bool
    operation: Literal["message", "forget"] = "message"
    refers_to_event_id: str | None = None
    supersedes_event_id: str | None = None
    overlay_id: str | None = None
    overlay_event_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvaluationLabel:
    schema_version: Literal[2]
    history_unit_id: str
    persona_id: str
    evaluation_event_id: str
    answer_key: str
    rubric: str | None = None
    incorrect_answers: list[str] = field(default_factory=list)
    strata: dict[str, Any] = field(default_factory=dict)
    source_record_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
