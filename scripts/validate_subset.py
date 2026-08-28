"""Validate a manifest plus its normalized event and label streams."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import jsonschema
import yaml

from llm_adversarial_information_attacks.datasets.io import read_jsonl
from llm_adversarial_information_attacks.datasets.validation import validate_records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--schemas", default="schemas")
    args = parser.parse_args()
    manifest_path = Path(args.manifest)
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    schema_root = Path(args.schemas)
    jsonschema.Draft202012Validator(
        json.loads((schema_root / "experiment.schema.json").read_text(encoding="utf-8"))
    ).validate(manifest)
    events_path = manifest_path.parent / manifest["dataset"]["events_path"]
    labels_path = manifest_path.parent / manifest["dataset"]["labels_path"]
    errors = validate_records(
        read_jsonl(events_path), read_jsonl(labels_path), schemas_dir=schema_root
    )
    if errors:
        raise SystemExit("Validation failed:\n- " + "\n- ".join(errors))
    print(f"Validated {manifest['experiment_id']}")


if __name__ == "__main__":
    main()
