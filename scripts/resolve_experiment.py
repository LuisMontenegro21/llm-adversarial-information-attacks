"""Validate and hash one schema-v2 run manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from llm_adversarial_information_attacks.datasets.experiments import resolve_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--out", required=True)
    parser.add_argument("--schemas", default="schemas")
    args = parser.parse_args()
    manifest = yaml.safe_load(Path(args.manifest).read_text(encoding="utf-8"))
    resolved = resolve_manifest(manifest, schemas_dir=args.schemas)
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(yaml.safe_dump(resolved, sort_keys=True), encoding="utf-8")
    print(f"Resolved {resolved['experiment_id']}: {resolved['manifest_hash']}")


if __name__ == "__main__":
    main()
