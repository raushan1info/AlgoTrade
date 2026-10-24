"""Load and validate YAML catalogs and named research experiments."""
from datetime import date
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPOSITORY_ROOT / "config"
CATALOG_FILES = ("providers", "datasets", "strategies", "experiments")


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return value


def validate_catalog(catalog: dict[str, Any]) -> None:
    """Validate catalog shape, references, provider settings, and strategy definitions."""
    for section in CATALOG_FILES:
        if not isinstance(catalog.get(section), dict) or not catalog[section]:
            raise ValueError(f"Configuration section '{section}' must be a non-empty mapping")

    for provider_id, provider in catalog["providers"].items():
        if not isinstance(provider, dict):
            raise ValueError(f"Provider '{provider_id}' must be a mapping")
        provider_type = provider.get("type")
        if provider_type not in {"synthetic", "yfinance", "csv", "rest_json", "broker_api"}:
            raise ValueError(f"Provider '{provider_id}' has unsupported type {provider_type!r}")
        if provider_type == "csv" and not provider.get("path"):
            raise ValueError(f"Provider '{provider_id}' of type csv requires path")
        if provider_type == "rest_json":
            url = provider.get("url")
            parsed = urlsplit(str(url or ""))
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"REST provider '{provider_id}' requires an absolute HTTP(S) url")
            timeout = float(provider.get("timeout_seconds", 30))
            if timeout <= 0:
                raise ValueError(f"REST provider '{provider_id}' timeout_seconds must be positive")
            auth = provider.get("auth", {})
            if auth:
                if not isinstance(auth, dict):
                    raise ValueError(f"REST provider '{provider_id}' auth must be a mapping")
                if auth.get("type") not in {"bearer", "api_key_header"} or not auth.get("token_env"):
                    raise ValueError(
                        f"REST provider '{provider_id}' auth requires type bearer/api_key_header "
                        "and token_env"
                    )
                if auth.get("type") == "api_key_header" and not auth.get("header_name"):
                    raise ValueError(f"REST provider '{provider_id}' api_key_header requires header_name")

    for dataset_id, dataset in catalog["datasets"].items():
        if not isinstance(dataset, dict):
            raise ValueError(f"Dataset '{dataset_id}' must be a mapping")
        provider_id = dataset.get("provider")
        if provider_id not in catalog["providers"]:
            raise ValueError(f"Dataset '{dataset_id}' references unknown provider '{provider_id}'")
        if not dataset.get("symbol"):
            raise ValueError(f"Dataset '{dataset_id}' must define symbol")
        interval = dataset.get("interval", "1d")
        if interval != "1d":
            raise ValueError(
                f"Dataset '{dataset_id}' requests unsupported interval {interval!r}; "
                "this version supports daily data only"
            )
        if dataset.get("data_kind", "synthetic" if catalog["providers"][provider_id]["type"] == "synthetic" else "ohlcv") not in {
            "synthetic", "ohlcv", "index", "future", "option", "option_chain"
        }:
            raise ValueError(f"Dataset '{dataset_id}' has an unsupported data_kind")

    # Reuse constructors to catch unknown strategy types and invalid parameter values early.
    from strategies.registry import create_strategy
    for strategy_id, definition in catalog["strategies"].items():
        if not isinstance(definition, dict):
            raise ValueError(f"Strategy '{strategy_id}' must be a mapping")
        create_strategy(strategy_id, definition)

    instruments = catalog.get("instruments", {})
    if instruments and not isinstance(instruments, dict):
        raise ValueError("Configuration section 'instruments' must be a mapping")
    for instrument_id, instrument in instruments.items():
        if not isinstance(instrument, dict) or not all(
            instrument.get(field) for field in ("exchange", "segment", "symbol", "kind")
        ):
            raise ValueError(f"Instrument '{instrument_id}' requires exchange, segment, symbol, and kind")
        if instrument["kind"] not in {"index", "equity", "future", "option"}:
            raise ValueError(f"Instrument '{instrument_id}' has unsupported kind")


def load_catalog(config_dir: str | Path | None = None) -> dict[str, Any]:
    """Load catalogs relative to the repository, not the caller's current directory."""
    root = Path(config_dir).expanduser().resolve() if config_dir is not None else CONFIG_DIR
    catalog = {
        section: _read_yaml(root / f"{section}.yaml").get(section, {})
        for section in CATALOG_FILES
    }
    catalog["defaults"] = _read_yaml(root / "defaults.yaml").get("defaults", {})
    instruments_path = root / "instruments.yaml"
    catalog["instruments"] = (
        _read_yaml(instruments_path).get("instruments", {}) if instruments_path.exists() else {}
    )
    validate_catalog(catalog)
    return catalog


def resolve_experiment(catalog: dict[str, Any], experiment_id: str) -> dict[str, Any]:
    """Resolve one experiment and validate its reusable catalog references."""
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
        unknown = sorted(set(values) - set(catalog[field]))
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

    settings = {
        **catalog["defaults"].get("backtest", {}),
        **experiment.get("backtest", {}),
    }
    initial_capital = float(settings.get("initial_capital", 100_000))
    cost_bps = float(settings.get("transaction_cost_bps", 10))
    risk_free_rate = float(settings.get("risk_free_rate", 0))
    if initial_capital <= 0:
        raise ValueError("backtest.initial_capital must be positive")
    if cost_bps < 0:
        raise ValueError("backtest.transaction_cost_bps cannot be negative")
    if risk_free_rate <= -1:
        raise ValueError("backtest.risk_free_rate must be greater than -1")
    experiment["backtest"] = {
        **settings,
        "initial_capital": initial_capital,
        "transaction_cost_bps": cost_bps,
        "risk_free_rate": risk_free_rate,
    }
    experiment["output_dir"] = str(experiment.get("output_dir", "reports"))
    experiment["combination_mode"] = experiment.get("combination_mode", "all")
    if experiment["combination_mode"] != "all":
        raise ValueError("Only combination_mode: all is currently supported")
    return experiment


def validate_experiment_readiness(
    catalog: dict[str, Any], experiment_id: str, *, check_local_files: bool = True
) -> list[str]:
    """Return actionable readiness warnings without making network requests."""
    from core.configuration.environment import load_environment

    load_environment()
    experiment = resolve_experiment(catalog, experiment_id)
    warnings: list[str] = []
    for dataset_id in experiment["datasets"]:
        dataset = catalog["datasets"][dataset_id]
        provider_id = dataset["provider"]
        provider = catalog["providers"][provider_id]
        provider_type = provider["type"]
        if provider_type == "synthetic":
            warnings.append(
                f"Dataset '{dataset_id}' uses synthetic data; results are not real-market evidence."
            )
        elif provider_type == "broker_api":
            warnings.append(
                f"Dataset '{dataset_id}' uses '{provider_id}', but broker_api is not implemented."
            )
        elif provider_type == "rest_json":
            host = urlsplit(provider["url"]).hostname or ""
            if host.endswith(".example.com") or host == "example.com":
                warnings.append(
                    f"Provider '{provider_id}' uses a placeholder example.com endpoint."
                )
            auth = provider.get("auth", {})
            token_env = auth.get("token_env") if isinstance(auth, dict) else None
            if token_env and not os.environ.get(token_env):
                warnings.append(
                    f"Provider '{provider_id}' requires environment variable '{token_env}'."
                )
        elif provider_type == "csv" and check_local_files:
            csv_path = Path(provider["path"]).expanduser()
            if not csv_path.is_absolute():
                csv_path = REPOSITORY_ROOT / csv_path
            if not csv_path.is_file():
                warnings.append(
                    f"Provider '{provider_id}' CSV file does not exist: {csv_path}"
                )
    return warnings
