"""Vectorized long-only backtest engine with next-bar execution."""
import pandas as pd
from analytics.metrics import calculate_metrics
from core.base.models import BacktestConfig, validate_ohlcv
from strategies.momentum import generate_signals


def run_strategy_backtest(market_data: pd.DataFrame, strategy, config: BacktestConfig | None = None
                          ) -> tuple[pd.DataFrame, dict[str, float]]:
    """Run a strategy with next-bar position application and turnover-based costs."""
    config = config or BacktestConfig()
    data = validate_ohlcv(market_data)
    signals = strategy.generate_signals(data)
    if "signal" not in signals:
        raise ValueError("Strategy output must contain a 'signal' column")
    signal = pd.to_numeric(signals["signal"], errors="raise").reindex(data.index)
    if signal.isna().any() or not signal.map(lambda value: pd.notna(value) and abs(value) != float("inf")).all():
        raise ValueError("Strategy signals must be finite values between 0 and 1")
    if not signal.between(0, 1).all():
        raise ValueError("Strategy signals must be finite values between 0 and 1")
    result = signals.reindex(data.index).copy()
    result["signal"] = signal.astype(float)
    result["market_return"] = data["Close"].pct_change().fillna(0.0)
    # Signal from close t is used for the following period, avoiding same-bar look-ahead.
    result["position"] = result["signal"].shift(1).fillna(0.0)
    result["turnover"] = result["position"].diff().abs().fillna(result["position"].abs())
    cost_rate = config.transaction_cost_bps / 10_000.0
    result["transaction_cost"] = result["turnover"] * cost_rate
    result["strategy_return"] = result["position"] * result["market_return"] - result["transaction_cost"]
    result["equity"] = config.initial_capital * (1.0 + result["strategy_return"]).cumprod()
    metrics = calculate_metrics(result["strategy_return"], result["equity"], config.risk_free_rate)
    position_change = result["position"].diff().fillna(result["position"])
    metrics["entry_count"] = float((position_change > 0).sum())
    metrics["exit_count"] = float((position_change < 0).sum())
    metrics["exposure_pct"] = float(result["position"].mean())
    metrics["total_turnover"] = float(result["turnover"].sum())
    metrics["initial_capital"] = float(config.initial_capital)
    metrics["final_equity"] = float(result["equity"].iloc[-1])
    return result, metrics


def run_momentum_backtest(market_data: pd.DataFrame, fast_window: int = 20, slow_window: int = 50,
                          config: BacktestConfig | None = None) -> tuple[pd.DataFrame, dict[str, float]]:
    """Backward-compatible wrapper for the original moving-average demo."""
    class _MomentumAdapter:
        def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
            return generate_signals(data["Close"], fast_window, slow_window)
    return run_strategy_backtest(market_data, _MomentumAdapter(), config)
