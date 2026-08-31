"""Compile a clean, matched-benign, or malicious overlay into an event stream."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from llm_adversarial_information_attacks.datasets.io import read_jsonl, write_jsonl
from llm_adversarial_information_attacks.datasets.overlays import compile_overlay


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", required=True)
    parser.add_argument("--overlay", required=True)
    parser.add_argument("--events-out", required=True)
    parser.add_argument("--metadata-out", required=True)
    parser.add_argument("--schemas", default="schemas")
    args = parser.parse_args()
    overlay = yaml.safe_load(Path(args.overlay).read_text(encoding="utf-8"))
    all_events = list(read_jsonl(args.events))
    selected = [
        event
        for event in all_events
        if event["history_unit_id"] == overlay["history_unit_id"]
    ]
    result = compile_overlay(selected, overlay, schemas_dir=args.schemas)
    write_jsonl(args.events_out, result.events)
    Path(args.metadata_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.metadata_out).write_text(
        json.dumps(result.metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Compiled {overlay['overlay_id']} into {len(result.events)} events")


if __name__ == "__main__":
    main()
