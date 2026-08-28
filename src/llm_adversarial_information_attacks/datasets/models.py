"""Canonical, mechanism-independent dataset records."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Role = Literal["user", "assistant", "system", "tool"]
ContentType = Literal["text", "image", "multimodal"]
EventSplit = Literal[
    "benign_ingestion",
    "pre_attack_probe",
    "attack_insertion",
    "delay_noise",
    "victim_probe",
    "recovery_probe",
    "unrelated_control_probe",
]


@dataclass(frozen=True, slots=True)
class Event:
    experiment_id: str
    persona_id: str
    session_id: str
    event_id: str
    sequence: int
    timestamp: str
    role: Role
    content: str | list[dict[str, Any]]
    content_type: ContentType
    topic: str
    split: EventSplit
    source_dataset: Literal["personamem_v1", "personamem_v2", "synthetic"]
    source_record_id: str
    allowed_for_memory: bool
    operation: Literal["message", "forget"] = "message"
    refers_to_event_id: str | None = None
    supersedes_event_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}


@dataclass(frozen=True, slots=True)
class EvaluationLabel:
    experiment_id: str
    persona_id: str
    evaluation_event_id: str
    answer_key: str
    rubric: str | None = None
    incorrect_answers: list[str] = field(default_factory=list)
    preference_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}
