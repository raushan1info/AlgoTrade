from datetime import date

import pandas as pd
import pytest

from backtesting.derivatives_engine import (
    DerivativesBacktestConfig,
    run_derivative_backtest,
)
from core.base.derivatives import DerivativeContract


class FixedSignalStrategy:
    def __init__(self, signals):
        self.signals = signals

    def generate_signals(self, data):
        return pd.DataFrame({"signal": self.signals}, index=data.index)


def sample_data():
    return pd.DataFrame(
        {
            "Open": [100, 110, 120, 115],
            "High": [105, 115, 125, 120],
            "Low": [95, 105, 115, 110],
            "Close": [100, 110, 120, 115],
            "Volume": [1000, 1000, 1000, 1000],
        },
        index=pd.date_range("2025-01-01", periods=4, freq="D"),
    )


def option_contract():
    return DerivativeContract(
        instrument_id="NSE-NIFTY-30Jan25-24000-CE",
        underlying="NIFTY",
        exchange="NSE",
        segment="FNO",
        expiry=date(2025, 1, 30),
        lot_size=25,
        tick_size=0.05,
        kind="option",
        strike=24000,
        option_type="CE",
    )


def test_derivative_backtest_uses_whole_lots_and_next_bar_signal():
    result, metrics = run_derivative_backtest(
        sample_data(),
        FixedSignalStrategy([1, 1, 0, 0]),
        option_contract(),
        DerivativesBacktestConfig(initial_capital=100_000, lots=1),
    )
    assert result["position_lots"].tolist() == [0, 1, 1, 0]
    assert metrics["lot_size"] == 25
    assert metrics["entry_count"] == 1
    assert metrics["exit_count"] == 1
    assert metrics["net_pnl"] == pytest.approx(250 - 125)


def test_futures_require_explicit_margin_assumption():
    future = DerivativeContract(
        instrument_id="NSE-NIFTY-30Jan25-FUT",
        underlying="NIFTY",
        exchange="NSE",
        segment="FNO",
        expiry=date(2025, 1, 30),
        lot_size=25,
        tick_size=0.05,
        kind="future",
    )
    with pytest.raises(ValueError, match="futures_margin_rate"):
        run_derivative_backtest(
            sample_data(), FixedSignalStrategy([1, 1, 1, 0]), future
        )


def test_derivative_backtest_rejects_fractional_signal():
    with pytest.raises(ValueError, match="between 0 and 1"):
        run_derivative_backtest(
            sample_data(), FixedSignalStrategy([0, 0.5, 0, 0]), option_contract()
        )


def test_futures_margin_must_be_explicitly_configured():
    future = DerivativeContract(
        instrument_id="NSE-NIFTY-30Jan25-FUT",
        underlying="NIFTY",
        exchange="NSE",
        segment="FNO",
        expiry=date(2025, 1, 30),
        lot_size=25,
        tick_size=0.05,
        kind="future",
    )
    with pytest.raises(ValueError, match="Required premium/margin"):
        run_derivative_backtest(
            sample_data(),
            FixedSignalStrategy([1, 1, 1, 0]),
            future,
            DerivativesBacktestConfig(initial_capital=1000, futures_margin_rate=0.2),
        )
