"""Normalizers for local PersonaMem exports.

Each benchmark question becomes an independent experiment. This deliberately
duplicates shared histories: it makes the temporal cutoff explicit and prevents
one evaluation probe from changing the state observed by another.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .models import EvaluationLabel, Event

_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def _identifier(value: Any) -> str:
    text = str(value).strip()
    safe = "".join(
        character if character.isalnum() or character in "-_" else "-"
        for character in text
    )
    return safe.strip("-") or hashlib.sha256(text.encode()).hexdigest()[:12]


def _timestamp(sequence: int) -> str:
    return (_BASE_TIME + timedelta(seconds=sequence)).isoformat().replace("+00:00", "Z")


def _message(value: Any) -> dict[str, Any]:
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


def _content_type(content: Any) -> str:
    if isinstance(content, list):
        types = {
            str(item.get("type", "text")) for item in content if isinstance(item, dict)
        }
        return "image" if types == {"image"} else "multimodal"
    return "text"


def _events_and_label(
    *,
    experiment_id: str,
    persona_id: str,
    source_dataset: str,
    source_record_id: str,
    topic: str,
    history: list[dict[str, Any]],
    query: dict[str, Any],
    answer_key: str,
    incorrect_answers: list[str] | None = None,
    preference_type: str | None = None,
) -> tuple[list[Event], EvaluationLabel]:
    events: list[Event] = []
    for sequence, raw_message in enumerate(history):
        content = raw_message.get("content", "")
        events.append(
            Event(
                experiment_id=experiment_id,
                persona_id=persona_id,
                session_id=f"{experiment_id}-history",
                event_id=f"{experiment_id}-e{sequence:06d}",
                sequence=sequence,
                timestamp=_timestamp(sequence),
                role=raw_message.get("role", "user"),
                content=content,
                content_type=_content_type(content),
                topic=topic,
                split="benign_ingestion",
                source_dataset=source_dataset,
                source_record_id=source_record_id,
                allowed_for_memory=True,
            )
        )

    sequence = len(events)
    evaluation_event_id = f"{experiment_id}-e{sequence:06d}"
    query_content = query.get("content", "")
    events.append(
        Event(
            experiment_id=experiment_id,
            persona_id=persona_id,
            session_id=f"{experiment_id}-evaluation",
            event_id=evaluation_event_id,
            sequence=sequence,
            timestamp=_timestamp(sequence),
            role=query.get("role", "user"),
            content=query_content,
            content_type=_content_type(query_content),
            topic=topic,
            split="victim_probe",
            source_dataset=source_dataset,
            source_record_id=source_record_id,
            allowed_for_memory=False,
        )
    )
    label = EvaluationLabel(
        experiment_id=experiment_id,
        persona_id=persona_id,
        evaluation_event_id=evaluation_event_id,
        answer_key=str(answer_key),
        incorrect_answers=incorrect_answers or [],
        preference_type=preference_type,
    )
    return events, label


def load_v1_contexts(path: str | Path) -> dict[str, list[dict[str, Any]]]:
    contexts: dict[str, list[dict[str, Any]]] = {}
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            context_id = row.get("shared_context_id", row.get("id"))
            context = row.get("context", row.get("messages", row.get("conversations")))
            if context_id is None and len(row) == 1:
                context_id, context = next(iter(row.items()))
            if context_id is None or not isinstance(context, list):
                raise ValueError(
                    "v1 context rows need an id and a context/messages list"
                )
            contexts[str(context_id)] = context
    return contexts


def normalize_v1(
    questions_csv: str | Path, contexts_jsonl: str | Path
) -> tuple[list[Event], list[EvaluationLabel]]:
    contexts = load_v1_contexts(contexts_jsonl)
    events: list[Event] = []
    labels: list[EvaluationLabel] = []
    with Path(questions_csv).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            persona_id = f"pmv1-{_identifier(row['persona_id'])}"
            record_id = _identifier(row["question_id"])
            experiment_id = f"pmv1-{record_id}"
            context = contexts[str(row["shared_context_id"])]
            cutoff = int(row["end_index_in_shared_context"])
            scenario_events, label = _events_and_label(
                experiment_id=experiment_id,
                persona_id=persona_id,
                source_dataset="personamem_v1",
                source_record_id=record_id,
                topic=row.get("topic", "unknown"),
                history=context[:cutoff],
                query=_message(row["user_question_or_message"]),
                answer_key=row["correct_answer"],
                incorrect_answers=_parse_options(
                    row.get("all_options", ""), row["correct_answer"]
                ),
                preference_type=row.get("question_type") or None,
            )
            events.extend(scenario_events)
            labels.append(label)
    return events, labels


def _parse_options(value: str, answer: str) -> list[str]:
    if not value:
        return []
    try:
        options = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return []
    return (
        [str(option) for option in options if str(option) != str(answer)]
        if isinstance(options, list)
        else []
    )


def normalize_v2(
    benchmark_csv: str | Path, histories_root: str | Path, size: str = "32k"
) -> tuple[list[Event], list[EvaluationLabel]]:
    root = Path(histories_root)
    events: list[Event] = []
    labels: list[EvaluationLabel] = []
    link_column = f"chat_history_{size}_link"
    with Path(benchmark_csv).open(encoding="utf-8-sig", newline="") as handle:
        for row_number, row in enumerate(csv.DictReader(handle)):
            record_id = _identifier(
                row.get("source_record_id") or f"{row['persona_id']}-{row_number}"
            )
            experiment_id = f"pmv2-{record_id}"
            persona_id = f"pmv2-{_identifier(row['persona_id'])}"
            link = row.get(link_column) or row.get("chat_history_link")
            if not link:
                raise ValueError(f"row {row_number + 2}: missing {link_column}")
            history_data = json.loads(
                (root / Path(link).name).read_text(encoding="utf-8")
            )
            if isinstance(history_data, dict):
                history_data = history_data.get(
                    "conversations", history_data.get("messages")
                )
            if not isinstance(history_data, list):
                raise TypeError(f"row {row_number + 2}: history must be a message list")
            scenario_events, label = _events_and_label(
                experiment_id=experiment_id,
                persona_id=persona_id,
                source_dataset="personamem_v2",
                source_record_id=record_id,
                topic=row.get("topic_query", "unknown"),
                history=history_data,
                query=_message(row["user_query"]),
                answer_key=row["correct_answer"],
                incorrect_answers=_parse_options(
                    row.get("incorrect_answers", ""), row["correct_answer"]
                ),
                preference_type=row.get("pref_type") or None,
            )
            events.extend(scenario_events)
            labels.append(label)
    return events, labels
