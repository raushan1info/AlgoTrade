"""Load and validate YAML catalogs and named research experiments."""
from datetime import date
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path("config")


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return value


def validate_catalog(catalog: dict[str, Any]) -> None:
    """Validate reusable dataset definitions and their provider references."""
    for section in ("providers", "datasets", "strategies", "experiments"):
        if not isinstance(catalog.get(section), dict) or not catalog[section]:
            raise ValueError(f"Configuration section '{section}' must be a non-empty mapping")

    for dataset_id, dataset in catalog["datasets"].items():
        if not isinstance(dataset, dict):
            raise ValueError(f"Dataset '{dataset_id}' must be a mapping")
        provider_id = dataset.get("provider")
        if provider_id not in catalog["providers"]:
            raise ValueError(
                f"Dataset '{dataset_id}' references unknown provider '{provider_id}'"
            )
        if not dataset.get("symbol"):
            raise ValueError(f"Dataset '{dataset_id}' must define symbol")
        interval = dataset.get("interval", "1d")
        if interval != "1d":
            raise ValueError(
                f"Dataset '{dataset_id}' requests unsupported interval {interval!r}; "
                "this version supports daily data only"
            )


def load_catalog(config_dir: str | Path = CONFIG_DIR) -> dict[str, Any]:
    root = Path(config_dir)
    catalog = {
        section: _read_yaml(root / f"{section}.yaml").get(section, {})
        for section in ("providers", "datasets", "strategies", "experiments")
    }
    catalog["defaults"] = _read_yaml(root / "defaults.yaml").get("defaults", {})
    validate_catalog(catalog)
    return catalog


def resolve_experiment(catalog: dict[str, Any], experiment_id: str) -> dict[str, Any]:
    validate_catalog(catalog)
    experiments = catalog["experiments"]
    if experiment_id not in experiments:
        choices = ", ".join(sorted(experiments))
        raise ValueError(f"Unknown experiment '{experiment_id}'. Available: {choices}")
    experiment = dict(experiments[experiment_id])
    for field in ("datasets", "strategies"):
        values = experiment.get(field)
        if not isinstance(values, list) or not values:
            raise ValueError(f"Experiment '{experiment_id}' must define a non-empty {field} list")
        if len(values) != len(set(values)):
            raise ValueError(f"Experiment '{experiment_id}' contains duplicate {field} IDs")
        registry = catalog[field]
        unknown = sorted(set(values) - set(registry))
        if unknown:
            raise ValueError(f"Experiment '{experiment_id}' references unknown {field}: {unknown}")

    period = experiment.get("period", {})
    if not isinstance(period, dict) or not period.get("start") or not period.get("end"):
        raise ValueError(f"Experiment '{experiment_id}' must define period.start and period.end")
    try:
        start = date.fromisoformat(str(period["start"]))
        end = date.fromisoformat(str(period["end"]))
    except ValueError as exc:
        raise ValueError("Experiment dates must use ISO format YYYY-MM-DD") from exc
    if start > end:
        raise ValueError(f"Experiment '{experiment_id}' start date must be <= end date")

    experiment["backtest"] = {
        **catalog["defaults"].get("backtest", {}),
        **experiment.get("backtest", {}),
    }
    if float(experiment["backtest"].get("initial_capital", 100_000)) <= 0:
        raise ValueError("backtest.initial_capital must be positive")
    if float(experiment["backtest"].get("transaction_cost_bps", 10)) < 0:
        raise ValueError("backtest.transaction_cost_bps cannot be negative")

    experiment["output_dir"] = experiment.get("output_dir", "reports")
    experiment["combination_mode"] = experiment.get("combination_mode", "all")
    if experiment["combination_mode"] != "all":
        raise ValueError("Only combination_mode: all is currently supported")
    return experiment
