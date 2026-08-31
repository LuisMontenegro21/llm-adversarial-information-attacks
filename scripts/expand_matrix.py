"""Expand a deterministic experiment matrix into resolved manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from llm_adversarial_information_attacks.datasets.experiments import expand_matrix


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("matrix")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--schemas", default="schemas")
    args = parser.parse_args()
    matrix = yaml.safe_load(Path(args.matrix).read_text(encoding="utf-8"))
    manifests = expand_matrix(matrix, schemas_dir=args.schemas)
    destination = Path(args.out_dir)
    destination.mkdir(parents=True, exist_ok=True)
    index: list[dict[str, str]] = []
    for manifest in manifests:
        path = destination / f"{manifest['experiment_id']}.yaml"
        path.write_text(yaml.safe_dump(manifest, sort_keys=True), encoding="utf-8")
        index.append(
            {
                "experiment_id": manifest["experiment_id"],
                "manifest_hash": manifest["manifest_hash"],
                "path": path.name,
            }
        )
    (destination / "index.json").write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Expanded {len(manifests)} manifests into {destination}")


if __name__ == "__main__":
    main()
