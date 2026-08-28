"""Build a deterministic, persona-disjoint subset from normalized JSONL."""

from __future__ import annotations

import argparse

from llm_adversarial_information_attacks.datasets.io import read_jsonl, write_jsonl
from llm_adversarial_information_attacks.datasets.subset import (
    filter_records,
    select_personas,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--personas", required=True, type=int)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--events-out", required=True)
    parser.add_argument("--labels-out", required=True)
    args = parser.parse_args()
    events = list(read_jsonl(args.events))
    labels = list(read_jsonl(args.labels))
    personas = select_personas(labels, args.personas, args.seed)
    subset_events, subset_labels = filter_records(events, labels, personas)
    write_jsonl(args.events_out, subset_events)
    write_jsonl(args.labels_out, subset_labels)
    print(
        f"Selected {len(personas)} personas, {len(subset_events)} events, and {len(subset_labels)} labels"
    )


if __name__ == "__main__":
    main()
