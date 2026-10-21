import numpy as np
import pandas as pd
import pytest

from backtesting.engine import run_momentum_backtest
from core.base.models import BacktestConfig, validate_ohlcv
from data.providers.synthetic import SyntheticMarketDataProvider
from strategies.momentum import generate_signals


def test_synthetic_provider_returns_valid_ohlcv():
    data = SyntheticMarketDataProvider().get_history(
        "TEST.NS", "2023-01-01", "2023-06-30"
    )
    assert not data.empty
    assert {"Open", "High", "Low", "Close", "Volume"}.issubset(data.columns)
    assert data.index.is_monotonic_increasing


def test_validation_rejects_missing_columns():
    with pytest.raises(ValueError, match="Missing OHLCV"):
        validate_ohlcv(pd.DataFrame({"Close": [100]}))


def test_strategy_does_not_signal_before_slow_window():
    signals = generate_signals(pd.Series(np.arange(1, 101, dtype=float)), 3, 5)
    assert (signals["signal"].iloc[:4] == 0).all()
    assert (signals["signal"].iloc[4:] == 1).all()


def test_backtest_outputs_finite_metrics_and_equity():
    data = SyntheticMarketDataProvider().get_history(
        "TEST.NS", "2020-01-01", "2022-12-31"
    )
    results, metrics = run_momentum_backtest(
        data, 5, 20, BacktestConfig(100_000, 10)
    )
    assert len(results) == len(data)
    assert np.isfinite(results["strategy_return"]).all()
    assert np.isfinite(list(metrics.values())).all()
    assert metrics["initial_capital"] == 100_000
    assert metrics["final_equity"] > 0


def test_invalid_window_configuration_fails():
    with pytest.raises(ValueError, match="fast_window"):
        generate_signals(pd.Series(np.arange(1, 100, dtype=float)), 20, 10)
