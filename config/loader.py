"""Load and validate YAML experiment configuration."""
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


def load_catalog(config_dir: str | Path = CONFIG_DIR) -> dict[str, Any]:
    root = Path(config_dir)
    catalog = {
        "providers": _read_yaml(root / "providers.yaml").get("providers", {}),
        "datasets": _read_yaml(root / "datasets.yaml").get("datasets", {}),
        "strategies": _read_yaml(root / "strategies.yaml").get("strategies", {}),
        "experiments": _read_yaml(root / "experiments.yaml").get("experiments", {}),
        "defaults": _read_yaml(root / "defaults.yaml").get("defaults", {}),
    }
    for section in ("providers", "datasets", "strategies", "experiments"):
        if not catalog[section]:
            raise ValueError(f"Configuration section '{section}' must not be empty")
    return catalog


def resolve_experiment(catalog: dict[str, Any], experiment_id: str) -> dict[str, Any]:
    experiments = catalog["experiments"]
    if experiment_id not in experiments:
        choices = ", ".join(sorted(experiments))
        raise ValueError(f"Unknown experiment '{experiment_id}'. Available: {choices}")
    experiment = dict(experiments[experiment_id])
    for field in ("datasets", "strategies"):
        values = experiment.get(field)
        if not isinstance(values, list) or not values:
            raise ValueError(f"Experiment '{experiment_id}' must define a non-empty {field} list")
        registry = catalog[field]
        unknown = sorted(set(values) - set(registry))
        if unknown:
            raise ValueError(f"Experiment '{experiment_id}' references unknown {field}: {unknown}")
    period = experiment.get("period", {})
    if not period.get("start") or not period.get("end"):
        raise ValueError(f"Experiment '{experiment_id}' must define period.start and period.end")
    if str(period["start"]) > str(period["end"]):
        raise ValueError(f"Experiment '{experiment_id}' start date must be <= end date")
    experiment["backtest"] = {**catalog["defaults"].get("backtest", {}),
                              **experiment.get("backtest", {})}
    experiment["output_dir"] = experiment.get("output_dir", "reports")
    experiment["combination_mode"] = experiment.get("combination_mode", "all")
    if experiment["combination_mode"] != "all":
        raise ValueError("Only combination_mode: all is currently supported")
    return experiment
