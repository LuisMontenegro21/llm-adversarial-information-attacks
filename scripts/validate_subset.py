"""Validate a schema-v2 manifest plus normalized event and label streams."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from llm_adversarial_information_attacks.datasets.experiments import validate_manifest
from llm_adversarial_information_attacks.datasets.io import read_jsonl
from llm_adversarial_information_attacks.datasets.validation import validate_records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--schemas", default="schemas")
    args = parser.parse_args()
    manifest_path = Path(args.manifest)
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    errors = validate_manifest(manifest, schemas_dir=args.schemas)
    events_path = manifest_path.parent / manifest["dataset"]["events_path"]
    labels_path = manifest_path.parent / manifest["dataset"]["labels_path"]
    errors.extend(
        validate_records(
            read_jsonl(events_path),
            read_jsonl(labels_path),
            schemas_dir=args.schemas,
        )
    )
    if errors:
        raise SystemExit("Validation failed:\n- " + "\n- ".join(errors))
    print(f"Validated {manifest['experiment_id']}")


if __name__ == "__main__":
    main()
