import numpy as np
import pandas as pd
import pytest

from backtesting.engine import run_momentum_backtest, run_strategy_backtest
from core.base.models import BacktestConfig
from data.providers.synthetic import SyntheticMarketDataProvider


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



class FixedSignalStrategy:
    def __init__(self, values):
        self.values = values

    def generate_signals(self, data):
        return pd.DataFrame({"signal": self.values}, index=data.index)


def test_close_signal_fills_next_open_and_does_not_capture_pre_entry_gap():
    data = pd.DataFrame(
        {
            "Open": [100.0, 120.0, 80.0],
            "High": [101.0, 121.0, 81.0],
            "Low": [99.0, 109.0, 79.0],
            "Close": [100.0, 110.0, 80.0],
            "Volume": [1000, 1000, 1000],
        },
        index=pd.date_range("2025-01-01", periods=3, freq="D"),
    )
    results, _ = run_strategy_backtest(
        data, FixedSignalStrategy([1.0, 0.0, 0.0]),
        BacktestConfig(initial_capital=100_000, transaction_cost_bps=0),
    )
    assert results["position"].tolist() == [0.0, 1.0, 0.0]
    # The day-1 +20% overnight gap happened before the entry at its open.
    assert results["strategy_return"].iloc[1] == pytest.approx(110.0 / 120.0 - 1.0)
    # The position held overnight from day 1 earns/loses the gap before exiting at day-2 open.
    assert results["strategy_return"].iloc[2] == pytest.approx(80.0 / 110.0 - 1.0)


def test_backtest_charges_entry_and_final_liquidation_costs():
    data = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 100.0],
            "High": [101.0, 101.0, 101.0],
            "Low": [99.0, 99.0, 99.0],
            "Close": [100.0, 100.0, 100.0],
            "Volume": [1000, 1000, 1000],
        },
        index=pd.date_range("2025-01-01", periods=3, freq="D"),
    )
    results, metrics = run_strategy_backtest(
        data, FixedSignalStrategy([1.0, 1.0, 1.0]),
        BacktestConfig(initial_capital=100_000, transaction_cost_bps=100),
    )
    assert results["turnover"].sum() == pytest.approx(2.0)
    assert results["transaction_cost"].sum() == pytest.approx(0.02)
    assert metrics["exit_count"] == 1.0
