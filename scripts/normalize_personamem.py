"""Normalize a local PersonaMem export into event and private-label JSONL."""

from __future__ import annotations

import argparse

from llm_adversarial_information_attacks.datasets.io import write_jsonl
from llm_adversarial_information_attacks.datasets.normalization import (
    normalize_v1,
    normalize_v2,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", choices=("v1", "v2"), required=True)
    parser.add_argument("--benchmark", required=True, help="Questions/benchmark CSV")
    parser.add_argument(
        "--contexts", required=True, help="v1 contexts JSONL or v2 history directory"
    )
    parser.add_argument("--size", default="32k", choices=("32k", "128k"))
    parser.add_argument("--events-out", required=True)
    parser.add_argument("--labels-out", required=True)
    args = parser.parse_args()
    if args.version == "v1":
        events, labels = normalize_v1(args.benchmark, args.contexts)
    else:
        events, labels = normalize_v2(args.benchmark, args.contexts, args.size)
    write_jsonl(args.events_out, (event.to_dict() for event in events))
    write_jsonl(args.labels_out, (label.to_dict() for label in labels))
    print(f"Wrote {len(events)} events and {len(labels)} private labels")


if __name__ == "__main__":
    main()
