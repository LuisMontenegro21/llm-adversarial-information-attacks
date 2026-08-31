"""Run-manifest validation, resolution, and deterministic matrix expansion."""

from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path
from typing import Any

import jsonschema

from .hashing import sha256_json

_ALIASES = {
    "mechanism": "condition.mechanism",
    "policy": "condition.write_policy",
    "delivery": "attack.delivery",
    "payload": "attack.payload",
    "attacker_knowledge": "attack.attacker_knowledge",
    "writer_model": "models.writer",
    "responder_model": "models.responder",
}


def validate_manifest(
    manifest: dict[str, Any], *, schemas_dir: str | Path
) -> list[str]:
    schema = json.loads(
        (Path(schemas_dir) / "experiment.schema.json").read_text(encoding="utf-8")
    )
    validator = jsonschema.Draft202012Validator(schema)
    errors = [error.message for error in validator.iter_errors(manifest)]
    condition = manifest.get("condition", {})
    attack = manifest.get("attack", {})
    models = manifest.get("models", {})
    policy = condition.get("write_policy")
    delivery = attack.get("delivery")
    writer = models.get("writer")
    if delivery == "direct_api" and policy != "direct":
        errors.append(
            "direct_api delivery is supported only with the direct write policy"
        )
    if policy == "direct" and writer is not None:
        errors.append("direct write policy requires models.writer to be null")
    if policy in {"shared_selective", "native_selective"} and writer is None:
        errors.append("selective write policies require a writer model")
    regime = condition.get("comparison_regime")
    if policy == "native_selective" and regime != "native_stack":
        errors.append("native_selective write policy requires the native_stack regime")
    if policy in {"direct", "shared_selective"} and regime != "controlled_component":
        errors.append(f"{policy} write policy requires the controlled_component regime")
    budget = attack.get("budget", {})
    expected_unit = "record" if delivery == "direct_api" else "interaction"
    if budget.get("unit") != expected_unit:
        errors.append(f"{delivery} delivery requires {expected_unit!r} budget units")
    recorded_hash = manifest.get("manifest_hash")
    if recorded_hash is not None:
        unhashed = copy.deepcopy(manifest)
        unhashed.pop("manifest_hash", None)
        if recorded_hash != sha256_json(unhashed):
            errors.append("manifest_hash does not match the resolved manifest")
    return errors


def resolve_manifest(
    manifest: dict[str, Any], *, schemas_dir: str | Path
) -> dict[str, Any]:
    resolved = copy.deepcopy(manifest)
    resolved.pop("manifest_hash", None)
    errors = validate_manifest(resolved, schemas_dir=schemas_dir)
    if errors:
        raise ValueError("invalid experiment manifest: " + "; ".join(errors))
    resolved["manifest_hash"] = sha256_json(resolved)
    return resolved


def expand_matrix(
    matrix: dict[str, Any], *, schemas_dir: str | Path
) -> list[dict[str, Any]]:
    if matrix.get("schema_version") != 2:
        raise ValueError("matrix schema_version must be 2")
    base = matrix.get("base_manifest")
    axes = matrix.get("axes")
    if not isinstance(base, dict) or not isinstance(axes, dict) or not axes:
        raise ValueError("matrix requires base_manifest and non-empty axes objects")
    axis_names = sorted(axes)
    axis_values: list[list[Any]] = []
    for name in axis_names:
        values = axes[name]
        if not isinstance(values, list) or not values:
            raise ValueError(f"matrix axis {name!r} must be a non-empty list")
        axis_values.append(values)

    manifests: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    for values in itertools.product(*axis_values):
        selections = dict(zip(axis_names, values, strict=True))
        if not _constraints_allow(selections, matrix.get("constraints", [])):
            continue
        manifest = copy.deepcopy(base)
        manifest.pop("manifest_hash", None)
        for name, value in selections.items():
            _set_path(manifest, _ALIASES.get(name, name), _axis_value(name, value))
        _set_derived_fields(manifest)
        cell_hash = sha256_json(selections)[:12]
        manifest["experiment_id"] = f"{matrix['matrix_id']}-{cell_hash}"
        errors = validate_manifest(manifest, schemas_dir=schemas_dir)
        if errors:
            raise ValueError(f"invalid matrix cell {selections}: " + "; ".join(errors))
        manifest_hash = sha256_json(manifest)
        if manifest_hash in seen_hashes:
            raise ValueError(f"matrix produced a duplicate cell: {selections}")
        seen_hashes.add(manifest_hash)
        manifest["manifest_hash"] = manifest_hash
        manifests.append(manifest)
    return sorted(manifests, key=lambda item: item["experiment_id"])


def _axis_value(name: str, value: Any) -> Any:
    if name not in {"writer_model", "responder_model"}:
        return value
    if value is None or value == "none":
        return None
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or ":" not in value:
        raise ValueError(f"model axis values must use provider:model-id: {value!r}")
    provider, model = value.split(":", 1)
    return {"provider": provider, "model": model, "config_ref": None}


def _set_derived_fields(manifest: dict[str, Any]) -> None:
    delivery = manifest.get("attack", {}).get("delivery")
    budget = manifest.get("attack", {}).get("budget")
    if isinstance(budget, dict):
        budget["unit"] = "record" if delivery == "direct_api" else "interaction"
    policy = manifest.get("condition", {}).get("write_policy")
    condition = manifest.get("condition")
    if isinstance(condition, dict):
        condition["comparison_regime"] = (
            "native_stack" if policy == "native_selective" else "controlled_component"
        )


def _set_path(target: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current = target
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


def _constraints_allow(selections: dict[str, Any], constraints: Any) -> bool:
    if not isinstance(constraints, list):
        raise TypeError("matrix constraints must be a list")
    for constraint in constraints:
        if not isinstance(constraint, dict):
            raise TypeError("each matrix constraint must be an object")
        when = constraint.get("when", {})
        if not _selection_matches(selections, when):
            continue
        required = constraint.get("require")
        forbidden = constraint.get("forbid")
        if required is not None and not _selection_matches(selections, required):
            return False
        if forbidden is not None and _selection_matches(selections, forbidden):
            return False
    return True


def _selection_matches(selections: dict[str, Any], expected: Any) -> bool:
    if not isinstance(expected, dict):
        raise TypeError("constraint clauses must be objects")
    for key, expected_value in expected.items():
        actual = selections.get(key)
        if isinstance(expected_value, list):
            if actual not in expected_value:
                return False
        elif actual != expected_value:
            return False
    return True
