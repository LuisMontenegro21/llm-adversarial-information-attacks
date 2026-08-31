"""Normalize local PersonaMem-v2 text exports into independent history units."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from .models import EvaluationLabel, Event, Role

_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_ROLES = {"user", "assistant", "system", "tool"}


def _identifier(value: Any) -> str:
    text = str(value).strip()
    safe = "".join(
        character if character.isalnum() or character in "-_" else "-"
        for character in text
    )
    return safe.strip("-") or hashlib.sha256(text.encode()).hexdigest()[:12]


def _stable_record_id(row: dict[str, str]) -> str:
    explicit = row.get("source_record_id") or row.get("question_id")
    if explicit:
        return _identifier(explicit)
    identity = {
        "persona_id": row.get("persona_id"),
        "chat_history_32k_link": row.get("chat_history_32k_link"),
        "user_query": row.get("user_query"),
        "correct_answer": row.get("correct_answer"),
        "topic_query": row.get("topic_query"),
        "preference": row.get("preference"),
    }
    digest = hashlib.sha256(
        json.dumps(identity, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()[:16]
    return f"q-{digest}"


def synthetic_timestamp(sequence: int) -> str:
    return (_BASE_TIME + timedelta(seconds=sequence)).isoformat().replace("+00:00", "Z")


def parse_message(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {"role": "user", "content": str(value)}
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(value)
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, SyntaxError, json.JSONDecodeError):
            pass
    return {"role": "user", "content": value}


def text_blocks(content: Any) -> list[dict[str, str]]:
    """Return canonical text blocks and reject PersonaMem-v2 multimodal data."""
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        blocks: list[dict[str, str]] = []
        for block in content:
            if not isinstance(block, dict) or block.get("type", "text") != "text":
                raise ValueError("only PersonaMem-v2 text content is in scope")
            text = block.get("text", block.get("content"))
            if not isinstance(text, str):
                raise TypeError("text content blocks require a string text field")
            blocks.append({"type": "text", "text": text})
        return blocks
    raise TypeError("message content must be a string or a list of text blocks")


def _role(value: Any) -> Role:
    role = str(value or "user").lower()
    if role not in _ROLES:
        raise ValueError(f"unsupported message role: {role!r}")
    return cast(Role, role)


def _parse_list(value: str | None) -> list[str]:
    if not value:
        return []
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except (ValueError, SyntaxError, json.JSONDecodeError):
            pass
    return []


def _history_path(root: Path, link: str) -> Path:
    normalized = Path(link.replace("\\", "/"))
    candidates = (root / normalized, root / normalized.name)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"history file not found below {root}: {link}")


def _load_history(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("conversations", data.get("messages"))
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise TypeError(f"{path}: history must be a list of message objects")
    return data


def _conversation_and_turn(
    message: dict[str, Any],
    *,
    history_unit_id: str,
    sequence: int,
    current_turn: int,
) -> tuple[str, int, str]:
    conversation = message.get("conversation_id") or message.get("session_id")
    conversation_id = _identifier(conversation or f"{history_unit_id}-history")
    if _role(message.get("role")) == "user" or sequence == 0:
        current_turn += 1
    raw_turn = message.get("turn_id")
    turn_id = _identifier(raw_turn or f"{conversation_id}-turn-{current_turn:06d}")
    return conversation_id, current_turn, turn_id


def normalize_v2(
    benchmark_csv: str | Path,
    histories_root: str | Path,
    *,
    source_revision: str,
    size: str = "32k",
) -> tuple[list[Event], list[EvaluationLabel]]:
    """Normalize one independent history unit per PersonaMem-v2 benchmark row."""
    if not source_revision.strip():
        raise ValueError("source_revision must be an immutable dataset revision")
    root = Path(histories_root)
    events: list[Event] = []
    labels: list[EvaluationLabel] = []
    link_column = f"chat_history_{size}_link"

    with Path(benchmark_csv).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"persona_id", "user_query", "correct_answer"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"benchmark CSV is missing columns: {sorted(missing)}")

        for row_number, row in enumerate(reader, start=2):
            source_record_id = _stable_record_id(row)
            history_unit_id = f"pmv2-{source_record_id}"
            persona_id = f"pmv2-p{_identifier(row['persona_id'])}"
            link = row.get(link_column) or row.get("chat_history_link")
            if not link:
                raise ValueError(f"row {row_number}: missing {link_column}")
            history = _load_history(_history_path(root, link))

            current_turn = -1
            scenario: list[Event] = []
            for sequence, message in enumerate(history):
                conversation_id, current_turn, turn_id = _conversation_and_turn(
                    message,
                    history_unit_id=history_unit_id,
                    sequence=sequence,
                    current_turn=current_turn,
                )
                scenario.append(
                    Event(
                        schema_version=2,
                        history_unit_id=history_unit_id,
                        persona_id=persona_id,
                        conversation_id=conversation_id,
                        turn_id=turn_id,
                        event_id=f"{history_unit_id}-e{sequence:06d}",
                        sequence=sequence,
                        timestamp=synthetic_timestamp(sequence),
                        timestamp_is_synthetic=True,
                        role=_role(message.get("role")),
                        content=text_blocks(message.get("content", "")),
                        content_type="text",
                        source_topic=str(message["topic"])
                        if message.get("topic")
                        else None,
                        experimental_topic=None,
                        split="benign_ingestion",
                        source_dataset="personamem_v2",
                        source_revision=source_revision,
                        source_record_id=f"{link}#{sequence}",
                        source_event_index=sequence,
                        source_origin="dataset",
                        allowed_for_memory=True,
                    )
                )

            query = parse_message(row["user_query"])
            query_sequence = len(scenario)
            evaluation_event_id = f"{history_unit_id}-eval"
            scenario.append(
                Event(
                    schema_version=2,
                    history_unit_id=history_unit_id,
                    persona_id=persona_id,
                    conversation_id=f"{history_unit_id}-evaluation",
                    turn_id=f"{history_unit_id}-evaluation-turn",
                    event_id=evaluation_event_id,
                    sequence=query_sequence,
                    timestamp=synthetic_timestamp(query_sequence),
                    timestamp_is_synthetic=True,
                    role=_role(query.get("role")),
                    content=text_blocks(query.get("content", "")),
                    content_type="text",
                    source_topic=None,
                    experimental_topic=row.get("topic_query") or None,
                    split="victim_probe",
                    source_dataset="personamem_v2",
                    source_revision=source_revision,
                    source_record_id=source_record_id,
                    source_event_index=query_sequence,
                    source_origin="dataset",
                    allowed_for_memory=False,
                )
            )
            incorrect = [
                option
                for option in _parse_list(row.get("incorrect_answers"))
                if option != row["correct_answer"]
            ]
            labels.append(
                EvaluationLabel(
                    schema_version=2,
                    history_unit_id=history_unit_id,
                    persona_id=persona_id,
                    evaluation_event_id=evaluation_event_id,
                    answer_key=row["correct_answer"],
                    incorrect_answers=incorrect,
                    strata={
                        "preference_type": row.get("pref_type") or "unclassified",
                        "topic": row.get("topic_query") or "unknown",
                        "owner": row.get("who") or "unknown",
                        "updated": _optional_bool(row.get("updated")),
                        "sensitive": _optional_bool(row.get("sensitive_info")),
                    },
                    source_record_id=source_record_id,
                )
            )
            events.extend(scenario)
    return events, labels


def _optional_bool(value: str | None) -> bool | None:
    if value is None or value == "":
        return None
    return str(value).strip().lower() in {"1", "true", "yes"}
