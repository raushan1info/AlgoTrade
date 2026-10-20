import pandas as pd
import pytest
from config.loader import load_catalog, resolve_experiment
from backtesting.runner import run_experiment
from strategies.registry import create_strategy


def test_catalog_and_experiment_references_validate():
    catalog = load_catalog()
    experiment = resolve_experiment(catalog, "full_matrix")
    assert len(experiment["datasets"]) == 3
    assert len(experiment["strategies"]) == 3


def test_unknown_experiment_fails_with_available_names():
    catalog = load_catalog()
    with pytest.raises(ValueError, match="Unknown experiment"):
        resolve_experiment(catalog, "not_a_real_experiment")


def test_strategy_registry_builds_known_strategies():
    catalog = load_catalog()
    for strategy_id in catalog["strategies"]:
        strategy = create_strategy(strategy_id, catalog["strategies"][strategy_id])
        assert hasattr(strategy, "generate_signals")


def test_experiment_runs_strategy_dataset_matrix(tmp_path):
    catalog = load_catalog()
    catalog["experiments"]["test_matrix"] = {
        "datasets": ["reliance_demo", "tcs_demo"],
        "strategies": ["ma_20_50", "rsi_14"],
        "period": {"start": "2022-01-01", "end": "2022-12-31"},
        "output_dir": str(tmp_path),
        "combination_mode": "all",
    }
    result = run_experiment(catalog, "test_matrix")
    assert len(result["summary"]) == 4
    assert result["summary"]["dataset_id"].nunique() == 2
    assert result["summary"]["strategy_id"].nunique() == 2
    assert result["summary_path"].exists()
    assert result["report_path"].exists()


def test_rsi_strategy_signal_is_binary():
    catalog = load_catalog()
    strategy = create_strategy("rsi_14", catalog["strategies"]["rsi_14"])
    data = pd.DataFrame({"Close": list(range(100, 70, -1)) + list(range(71, 110))})
    signals = strategy.generate_signals(data)
    assert set(signals["signal"].unique()).issubset({0.0, 1.0})
