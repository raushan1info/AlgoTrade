"""Separate, conservative lot-based backtester for one exact F&O contract.

This is a research engine, not a broker simulator. It supports long/flat signals only,
charges configurable turnover costs, and requires an explicit futures margin assumption.
It does not model expiry settlement, intraday margin, option exercise, or short-option risk.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.base.derivatives import DerivativeContract
from core.base.models import validate_ohlcv


@dataclass(frozen=True)
class DerivativesBacktestConfig:
    initial_capital: float = 100_000.0
    lots: int = 1
    transaction_cost_bps: float = 0.0
    slippage_bps: float = 0.0
    futures_margin_rate: float | None = None
    force_close_at_end: bool = True

    def __post_init__(self) -> None:
        if not np.isfinite(self.initial_capital) or self.initial_capital <= 0:
            raise ValueError("initial_capital must be finite and positive")
        if self.lots <= 0:
            raise ValueError("lots must be a positive integer")
        if self.transaction_cost_bps < 0 or not np.isfinite(self.transaction_cost_bps):
            raise ValueError("transaction_cost_bps must be finite and non-negative")
        if self.slippage_bps < 0 or not np.isfinite(self.slippage_bps):
            raise ValueError("slippage_bps must be finite and non-negative")
        if self.futures_margin_rate is not None and not (
            np.isfinite(self.futures_margin_rate) and 0 < self.futures_margin_rate <= 1
        ):
            raise ValueError("futures_margin_rate must be between 0 and 1")


def run_derivative_backtest(
    market_data: pd.DataFrame,
    strategy,
    contract: DerivativeContract,
    config: DerivativesBacktestConfig | None = None,
) -> tuple[pd.DataFrame, dict[str, float | str]]:
    """Backtest one exact derivative contract using whole lots and long/flat signals.

    A close-derived signal is filled at the next bar's open. The previous position earns
    the overnight gap and the new position earns the open-to-close move. Options are
    charged their premium notional for capital requirement; futures use the supplied margin rate.
    """
    config = config or DerivativesBacktestConfig()
    data = validate_ohlcv(market_data)
    if contract.kind == "future" and config.futures_margin_rate is None:
        raise ValueError(
            "Set futures_margin_rate from a documented, date-appropriate margin source; "
            "the engine will not assume a universal futures margin."
        )

    signals = strategy.generate_signals(data)
    if "signal" not in signals:
        raise ValueError("Strategy output must contain a 'signal' column")
    signal = pd.to_numeric(signals["signal"], errors="raise").reindex(data.index)
    if signal.isna().any() or not np.isfinite(signal.to_numpy(dtype=float)).all():
        raise ValueError("Strategy signals must be finite and present for every candle")
    if not signal.between(0, 1).all():
        raise ValueError("Derivative engine currently supports long/flat signals in [0, 1] only")

    result = data.copy()
    result["signal"] = signal.astype(float)
    result["position_lots"] = (result["signal"].shift(1).fillna(0) > 0).astype(int) * config.lots
    result["previous_position_lots"] = result["position_lots"].shift(1).fillna(0)
    overnight_change = (result["Open"] - result["Close"].shift(1)).fillna(0.0)
    intraday_change = result["Close"] - result["Open"]
    # The old position owns the overnight gap; the newly filled position owns the intraday move.
    result["gross_pnl"] = (
        result["previous_position_lots"] * contract.lot_size * overnight_change
        + result["position_lots"] * contract.lot_size * intraday_change
    )
    result["position_change_lots"] = result["position_lots"].diff().fillna(
        result["position_lots"]
    ).abs()
    result["turnover_notional"] = (
        result["position_change_lots"] * contract.lot_size * result["Open"]
    )
    result["transaction_cost"] = (
        result["turnover_notional"] * config.transaction_cost_bps / 10_000.0
    )
    result["slippage_cost"] = result["turnover_notional"] * config.slippage_bps / 10_000.0
    if config.force_close_at_end and not result.empty:
        final_exit_notional = (
            result["position_lots"].iloc[-1] * contract.lot_size * result["Close"].iloc[-1]
        )
        result.iloc[-1, result.columns.get_loc("turnover_notional")] += final_exit_notional
        result.iloc[-1, result.columns.get_loc("transaction_cost")] += (
            final_exit_notional * config.transaction_cost_bps / 10_000.0
        )
        result.iloc[-1, result.columns.get_loc("slippage_cost")] += (
            final_exit_notional * config.slippage_bps / 10_000.0
        )
    result["net_pnl"] = (
        result["gross_pnl"] - result["transaction_cost"] - result["slippage_cost"]
    )
    result["equity"] = config.initial_capital + result["net_pnl"].cumsum()
    if (result["equity"] <= 0).any():
        raise ValueError("Backtest equity became non-positive; review contract sizing and assumptions")

    if contract.kind == "option":
        result["capital_required"] = (
            result["position_lots"] * contract.lot_size * result["Close"]
        )
    else:
        result["capital_required"] = (
            result["position_lots"] * contract.lot_size * result["Close"]
            * float(config.futures_margin_rate)
        )
    result["capital_utilization"] = result["capital_required"] / result["equity"]
    if (result["capital_required"] > result["equity"]).any():
        raise ValueError(
            "Required premium/margin exceeds simulated equity. Reduce lots or capital "
            "assumptions; futures margin is only an approximation supplied by the user."
        )

    returns = result["equity"].pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    total_return = float(result["equity"].iloc[-1] / config.initial_capital - 1.0)
    periods = max(len(result) - 1, 1)
    cagr = float((result["equity"].iloc[-1] / config.initial_capital) ** (252 / periods) - 1.0)
    volatility = float(returns.std(ddof=1)) if len(returns) > 1 else 0.0
    sharpe = float(returns.mean() / volatility * np.sqrt(252)) if volatility > 0 else 0.0
    drawdown = result["equity"] / result["equity"].cummax() - 1.0
    position_change = result["position_lots"].diff().fillna(result["position_lots"])
    if config.force_close_at_end and not result.empty and result["position_lots"].iloc[-1] > 0:
        metrics_exit_count = float((position_change < 0).sum() + 1)
    else:
        metrics_exit_count = float((position_change < 0).sum())
    metrics: dict[str, float | str] = {
        "instrument_id": contract.instrument_id,
        "contract_kind": contract.kind,
        "lot_size": float(contract.lot_size),
        "lots": float(config.lots),
        "initial_capital": float(config.initial_capital),
        "final_equity": float(result["equity"].iloc[-1]),
        "net_pnl": float(result["net_pnl"].sum()),
        "total_return": total_return,
        "cagr": cagr,
        "sharpe_ratio": sharpe,
        "max_drawdown": float(drawdown.min()),
        "entry_count": float((position_change > 0).sum()),
        "exit_count": metrics_exit_count,
        "transaction_cost_total": float(result["transaction_cost"].sum()),
        "slippage_cost_total": float(result["slippage_cost"].sum()),
        "max_capital_utilization": float(result["capital_utilization"].max()),
        "trading_days": float(len(result)),
    }
    return result, metrics
