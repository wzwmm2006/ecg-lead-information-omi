from __future__ import annotations

from pathlib import Path, PurePath
from typing import Any

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_SECTIONS = {"study", "configuration", "paths", "data", "model", "training", "evaluation"}


def load_config(path: str | Path) -> dict[str, Any]:
    """Load and validate one complete study configuration."""
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = Path.cwd() / config_path
    with config_path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a YAML mapping")
    missing = REQUIRED_SECTIONS - set(config)
    if missing:
        raise ValueError(f"Missing configuration sections: {sorted(missing)}")
    for name, value in config["paths"].items():
        candidate = PurePath(str(value))
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"paths.{name} must be repository-relative: {value}")
    config["_config_path"] = config_path
    config["_repository_root"] = REPOSITORY_ROOT
    validate_scientific_constants(config)
    return config


def validate_scientific_constants(config: dict[str, Any]) -> None:
    """Reject accidental changes to frozen dimensions and primary settings."""
    data = config["data"]
    training = config["training"]
    evaluation = config["evaluation"]
    expected = {
        "study.base_seed": (config["study"]["base_seed"], 20260813),
        "data.sampling_rate_hz": (data["sampling_rate_hz"], 500),
        "data.input_samples": (data["input_samples"], 5000),
        "data.output_samples": (data["output_samples"], 500),
        "training.folds": (training["folds"], 5),
        "training.epochs": (training["epochs"], 10),
        "training.batch_size": (training["batch_size"], 256),
        "evaluation.target_sensitivity": (evaluation["target_sensitivity"], 0.95),
        "evaluation.bootstrap_replicates": (evaluation["bootstrap_replicates"], 1000),
    }
    changed = [name for name, (actual, frozen) in expected.items() if actual != frozen]
    if changed:
        raise ValueError(f"Frozen scientific settings changed: {', '.join(changed)}")


def repository_path(config: dict[str, Any], name: str) -> Path:
    """Return an absolute runtime path from a repository-relative setting."""
    return config["_repository_root"] / Path(config["paths"][name])

