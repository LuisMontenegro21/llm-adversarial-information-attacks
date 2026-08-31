"""Normalize a local PersonaMem-v2 text export into schema-v2 JSONL."""

from __future__ import annotations

import argparse

from llm_adversarial_information_attacks.datasets.io import write_jsonl
from llm_adversarial_information_attacks.datasets.normalization import normalize_v2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--benchmark", required=True, help="PersonaMem-v2 benchmark CSV"
    )
    parser.add_argument(
        "--histories", required=True, help="Downloaded history directory"
    )
    parser.add_argument("--revision", required=True, help="Immutable dataset revision")
    parser.add_argument("--size", default="32k", choices=("32k", "128k"))
    parser.add_argument("--events-out", required=True)
    parser.add_argument("--labels-out", required=True)
    args = parser.parse_args()
    events, labels = normalize_v2(
        args.benchmark,
        args.histories,
        source_revision=args.revision,
        size=args.size,
    )
    write_jsonl(args.events_out, (event.to_dict() for event in events))
    write_jsonl(args.labels_out, (label.to_dict() for label in labels))
    print(f"Wrote {len(events)} events and {len(labels)} evaluator-only labels")


if __name__ == "__main__":
    main()
