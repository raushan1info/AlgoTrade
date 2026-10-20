"""Performance metrics for daily strategy returns."""
import numpy as np
import pandas as pd


def calculate_metrics(returns: pd.Series, equity_curve: pd.Series, risk_free_rate: float = 0.0) -> dict[str, float]:
    returns = returns.astype(float).dropna()
    if returns.empty:
        raise ValueError("At least one daily return is required")
    total_return = float(equity_curve.iloc[-1] / equity_curve.iloc[0] - 1.0)
    years = len(returns) / 252.0
    cagr = float((1.0 + total_return) ** (1.0 / years) - 1.0) if years > 0 and total_return > -1 else -1.0
    daily_rf = (1.0 + risk_free_rate) ** (1.0 / 252.0) - 1.0
    excess = returns - daily_rf
    daily_std = returns.std(ddof=1)
    volatility = float(daily_std * np.sqrt(252)) if len(returns) > 1 else 0.0
    sharpe = float(excess.mean() / daily_std * np.sqrt(252)) if len(returns) > 1 and daily_std > 0 else 0.0
    drawdown = equity_curve / equity_curve.cummax() - 1.0
    return {"total_return": total_return, "cagr": cagr, "annualized_volatility": volatility,
            "sharpe_ratio": sharpe, "max_drawdown": float(drawdown.min()), "trading_days": float(len(returns))}
