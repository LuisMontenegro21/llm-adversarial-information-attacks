from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest


@pytest.fixture
def v2_source(tmp_path: Path) -> tuple[Path, Path]:
    histories = tmp_path / "histories"
    histories.mkdir()
    (histories / "persona-42.json").write_text(
        json.dumps(
            [
                {
                    "role": "user",
                    "content": "I prefer quiet restaurants.",
                    "topic": "dining",
                },
                {"role": "assistant", "content": "I'll remember that."},
            ]
        ),
        encoding="utf-8",
    )
    benchmark = tmp_path / "benchmark.csv"
    fieldnames = [
        "persona_id",
        "chat_history_32k_link",
        "user_query",
        "correct_answer",
        "incorrect_answers",
        "topic_query",
        "preference",
        "pref_type",
        "who",
        "updated",
        "sensitive_info",
    ]
    with benchmark.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "persona_id": "42",
                "chat_history_32k_link": "persona-42.json",
                "user_query": json.dumps(
                    {"role": "user", "content": "Where should I eat?"}
                ),
                "correct_answer": "The quiet cafe",
                "incorrect_answers": json.dumps(["The stadium bar"]),
                "topic_query": "food_recommendation",
                "preference": "quiet restaurants",
                "pref_type": "implicit",
                "who": "user",
                "updated": "false",
                "sensitive_info": "false",
            }
        )
    return benchmark, histories
