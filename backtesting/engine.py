"""Vectorized long-only backtest engine with next-bar execution."""
import pandas as pd
from analytics.metrics import calculate_metrics
from core.base.models import BacktestConfig, validate_ohlcv
from strategies.momentum import generate_signals


def run_momentum_backtest(market_data: pd.DataFrame, fast_window: int = 20, slow_window: int = 50,
                          config: BacktestConfig | None = None) -> tuple[pd.DataFrame, dict[str, float]]:
    config = config or BacktestConfig()
    data = validate_ohlcv(market_data)
    result = generate_signals(data["Close"], fast_window, slow_window)
    result["market_return"] = data["Close"].pct_change().fillna(0.0)
    # Signal from close t is used for the following period, avoiding same-bar look-ahead.
    result["position"] = result["signal"].shift(1).fillna(0.0)
    result["turnover"] = result["position"].diff().abs().fillna(result["position"].abs())
    cost_rate = config.transaction_cost_bps / 10_000.0
    result["strategy_return"] = result["position"] * result["market_return"] - result["turnover"] * cost_rate
    result["equity"] = config.initial_capital * (1.0 + result["strategy_return"]).cumprod()
    metrics = calculate_metrics(result["strategy_return"], result["equity"], config.risk_free_rate)
    metrics["initial_capital"] = float(config.initial_capital)
    metrics["final_equity"] = float(result["equity"].iloc[-1])
    return result, metrics
