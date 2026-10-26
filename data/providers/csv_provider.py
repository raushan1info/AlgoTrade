"""Local CSV market-data provider."""
from pathlib import Path

import pandas as pd

from core.base.models import validate_ohlcv
from core.market_data.base import MarketDataProvider


class CSVMarketDataProvider(MarketDataProvider):
    def __init__(self, path: str):
        configured_path = Path(path).expanduser()
        if not configured_path.is_absolute():
            configured_path = Path(__file__).resolve().parents[2] / configured_path
        self.path = configured_path.resolve()

    def get_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        if not self.path.is_file():
            raise FileNotFoundError(f"CSV market data not found: {self.path}")
        frame = pd.read_csv(self.path)
        date_column = next(
            (column for column in frame.columns
             if str(column).strip().lower() in {"date", "datetime", "timestamp"}),
            None,
        )
        if date_column is None:
            raise ValueError(f"CSV must contain a Date/Datetime/Timestamp column: {self.path}")
        frame[date_column] = pd.to_datetime(frame[date_column], errors="raise")
        frame = frame.set_index(date_column).sort_index()
        start_date = pd.Timestamp(start)
        end_date = pd.Timestamp(end)
        frame = frame.loc[(frame.index >= start_date) & (frame.index <= end_date)]
        if frame.empty:
            raise ValueError(f"No rows in {self.path} for {start} through {end}")
        frame.columns = [str(column).strip().title() for column in frame.columns]
        required = ["Open", "High", "Low", "Close", "Volume"]
        missing = set(required).difference(frame.columns)
        if missing:
            raise ValueError(f"CSV is missing OHLCV columns: {sorted(missing)}")
        return validate_ohlcv(frame[required])
