"""Shared, provider-independent data models."""
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float = 100_000.0
    transaction_cost_bps: float = 10.0
    risk_free_rate: float = 0.0

    def __post_init__(self) -> None:
        if not np.isfinite(self.initial_capital) or self.initial_capital <= 0:
            raise ValueError("initial_capital must be finite and positive")
        if not np.isfinite(self.transaction_cost_bps) or self.transaction_cost_bps < 0:
            raise ValueError("transaction_cost_bps must be finite and non-negative")
        if not np.isfinite(self.risk_free_rate) or self.risk_free_rate <= -1:
            raise ValueError("risk_free_rate must be finite and greater than -1")


def validate_ohlcv(data: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize a date-indexed OHLCV frame without silently repairing it."""
    required = ["Open", "High", "Low", "Close", "Volume"]
    missing = set(required).difference(data.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")
    if data.empty:
        raise ValueError("Market data is empty")
    frame = data.copy()
    frame.index = pd.to_datetime(frame.index, errors="raise")
    if frame.index.isna().any():
        raise ValueError("Market data index cannot contain invalid timestamps")
    frame = frame.sort_index()
    if frame.index.has_duplicates:
        raise ValueError("Market data contains duplicate timestamps")
    for column in required:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    prices = frame[["Open", "High", "Low", "Close"]]
    if not np.isfinite(prices.to_numpy(dtype=float)).all():
        raise ValueError("OHLC prices must be finite")
    if prices.isna().any().any():
        raise ValueError("OHLC prices cannot contain null values")
    if (prices <= 0).any().any():
        raise ValueError("OHLC prices must be positive")
    if not np.isfinite(frame["Volume"].to_numpy(dtype=float)).all():
        raise ValueError("Volume must be finite")
    if frame["Volume"].isna().any():
        raise ValueError("Volume cannot contain null values")
    if (frame["Volume"] < 0).any():
        raise ValueError("Volume cannot be negative")
    invalid_range = (
        (frame["High"] < frame[["Open", "Close", "Low"]].max(axis=1))
        | (frame["Low"] > frame[["Open", "Close", "High"]].min(axis=1))
    )
    if invalid_range.any():
        raise ValueError("OHLC rows must satisfy High >= Open/Close/Low and Low <= Open/Close/High")
    return frame[required]
