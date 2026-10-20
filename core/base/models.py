"""Shared, provider-independent data models."""
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class BacktestConfig:
    initial_capital: float = 100_000.0
    transaction_cost_bps: float = 10.0
    risk_free_rate: float = 0.0

    def __post_init__(self) -> None:
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if self.transaction_cost_bps < 0:
            raise ValueError("transaction_cost_bps cannot be negative")


def validate_ohlcv(data: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize an OHLCV frame indexed by date."""
    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")
    if data.empty:
        raise ValueError("Market data is empty")
    frame = data.copy()
    frame.index = pd.to_datetime(frame.index)
    frame = frame.sort_index()
    if frame.index.has_duplicates:
        raise ValueError("Market data contains duplicate timestamps")
    for column in required:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    if frame[["Open", "High", "Low", "Close"]].isna().any().any():
        raise ValueError("OHLC prices cannot contain null values")
    if (frame[["Open", "High", "Low", "Close"]] <= 0).any().any():
        raise ValueError("OHLC prices must be positive")
    if (frame["Volume"] < 0).any():
        raise ValueError("Volume cannot be negative")
    return frame
