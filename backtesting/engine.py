"""Long-only backtest engine with close-derived signals and next-open execution."""
import numpy as np
import pandas as pd

from analytics.metrics import calculate_metrics
from core.base.models import BacktestConfig, validate_ohlcv
from strategies.momentum import generate_signals


def run_strategy_backtest(
    market_data: pd.DataFrame, strategy, config: BacktestConfig | None = None
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Backtest daily signals with next-open fills, overnight gaps, and end liquidation.

    A signal observed at close[t-1] determines the target position at open[t]. The
    previous position earns the close[t-1] -> open[t] gap; the new position earns
    open[t] -> close[t]. Costs are charged on position changes at the open and on
    liquidation at the final close. This is still a bar-based approximation: it does
    not model intraday order books, bid/ask quotes, liquidity or partial fills.
    """
    config = config or BacktestConfig()
    data = validate_ohlcv(market_data)
    signals = strategy.generate_signals(data)
    if "signal" not in signals:
        raise ValueError("Strategy output must contain a 'signal' column")
    signal = pd.to_numeric(signals["signal"], errors="raise").reindex(data.index)
    if signal.isna().any() or not np.isfinite(signal.to_numpy(dtype=float)).all():
        raise ValueError("Strategy signals must be finite and present for every candle")
    if not signal.between(0, 1).all():
        raise ValueError("Strategy signals must be finite values between 0 and 1")

    result = signals.reindex(data.index).copy()
    result["signal"] = signal.astype(float)
    result["Open"] = data["Open"]
    result["Close"] = data["Close"]
    result["market_return"] = data["Close"].pct_change().fillna(0.0)

    # The target is entered at the next bar's open; the current bar's close signal
    # cannot affect the current bar's position or return.
    result["position"] = result["signal"].shift(1).fillna(0.0)
    previous_position = result["position"].shift(1).fillna(0.0)
    overnight_return = (data["Open"] / data["Close"].shift(1) - 1.0).fillna(0.0)
    intraday_return = data["Close"] / data["Open"] - 1.0
    result["overnight_return"] = overnight_return
    result["intraday_return"] = intraday_return
    result["gross_strategy_return"] = (
        (1.0 + previous_position * overnight_return)
        * (1.0 + result["position"] * intraday_return)
        - 1.0
    )

    result["turnover"] = result["position"].diff().abs().fillna(result["position"].abs())
    # The final open position is liquidated at the final close, with an exit cost.
    if not result.empty and result["position"].iloc[-1] > 0:
        result.iloc[-1, result.columns.get_loc("turnover")] += abs(
            float(result["position"].iloc[-1])
        )
    transaction_rate = config.transaction_cost_bps / 10_000.0
    slippage_rate = config.slippage_bps / 10_000.0
    result["transaction_cost"] = result["turnover"] * transaction_rate
    result["slippage_cost"] = result["turnover"] * slippage_rate
    result["strategy_return"] = (
        result["gross_strategy_return"] - result["transaction_cost"] - result["slippage_cost"]
    )
    result["equity"] = config.initial_capital * (1.0 + result["strategy_return"]).cumprod()
    if not np.isfinite(result["equity"].to_numpy(dtype=float)).all() or (result["equity"] <= 0).any():
        raise ValueError("Backtest equity became non-positive or non-finite; review assumptions")

    metrics = calculate_metrics(result["strategy_return"], result["equity"], config.risk_free_rate)
    position_change = result["position"].diff().fillna(result["position"])
    metrics["entry_count"] = float((position_change > 0).sum())
    metrics["exit_count"] = float((position_change < 0).sum())
    if not result.empty and result["position"].iloc[-1] > 0:
        metrics["exit_count"] += 1.0
    metrics["exposure_pct"] = float(result["position"].mean())
    metrics["total_turnover"] = float(result["turnover"].sum())
    metrics["transaction_cost_total"] = float(
        (result["transaction_cost"] * result["equity"].shift(1).fillna(config.initial_capital)).sum()
    )
    metrics["slippage_cost_total"] = float(
        (result["slippage_cost"] * result["equity"].shift(1).fillna(config.initial_capital)).sum()
    )
    metrics["initial_capital"] = float(config.initial_capital)
    metrics["final_equity"] = float(result["equity"].iloc[-1])
    metrics["execution_model_next_open"] = 1.0
    return result, metrics


def run_momentum_backtest(
    market_data: pd.DataFrame,
    fast_window: int = 20,
    slow_window: int = 50,
    config: BacktestConfig | None = None,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Backward-compatible wrapper for the original moving-average demo."""

    class _MomentumAdapter:
        def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
            return generate_signals(data["Close"], fast_window, slow_window)

    return run_strategy_backtest(market_data, _MomentumAdapter(), config)
