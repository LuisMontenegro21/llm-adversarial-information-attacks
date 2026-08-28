"""Deterministic persona-level subset selection."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Iterable
from typing import Any


def select_personas(
    labels: Iterable[dict[str, Any]], count: int, seed: int
) -> list[str]:
    """Select personas reproducibly while round-robining preference strata."""
    if count < 1:
        raise ValueError("count must be positive")
    strata: dict[str, set[str]] = defaultdict(set)
    all_personas: set[str] = set()
    for label in labels:
        persona = str(label["persona_id"])
        stratum = str(label.get("preference_type") or "unclassified")
        strata[stratum].add(persona)
        all_personas.add(persona)
    if count > len(all_personas):
        raise ValueError(
            f"requested {count} personas, but only {len(all_personas)} are available"
        )

    def rank(persona: str) -> str:
        return hashlib.sha256(f"{seed}:{persona}".encode()).hexdigest()

    buckets = {key: sorted(values, key=rank) for key, values in sorted(strata.items())}
    selected: list[str] = []
    while len(selected) < count:
        progressed = False
        for bucket in buckets.values():
            while bucket and bucket[0] in selected:
                bucket.pop(0)
            if bucket and len(selected) < count:
                selected.append(bucket.pop(0))
                progressed = True
        if not progressed:
            break
    return selected


def filter_records(
    events: Iterable[dict[str, Any]],
    labels: Iterable[dict[str, Any]],
    persona_ids: Iterable[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected = set(persona_ids)
    subset_events = [event for event in events if event["persona_id"] in selected]
    subset_labels = [label for label in labels if label["persona_id"] in selected]
    subset_events.sort(
        key=lambda item: (item["experiment_id"], item["sequence"], item["event_id"])
    )
    subset_labels.sort(
        key=lambda item: (item["experiment_id"], item["evaluation_event_id"])
    )
    return subset_events, subset_labels
