import numpy as np

from backtesting.engine import run_momentum_backtest
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
