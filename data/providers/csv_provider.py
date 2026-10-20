"""Local CSV market-data provider."""
from pathlib import Path
import pandas as pd
from core.base.models import validate_ohlcv
from core.market_data.base import MarketDataProvider


class CSVMarketDataProvider(MarketDataProvider):
    def __init__(self, path: str):
        self.path = Path(path)

    def get_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        if not self.path.exists():
            raise FileNotFoundError(f"CSV market data not found: {self.path}")
        frame = pd.read_csv(self.path)
        date_column = next((c for c in frame.columns if c.lower() in {"date", "datetime", "timestamp"}), None)
        if date_column is None:
            raise ValueError(f"CSV must contain a Date/Datetime/Timestamp column: {self.path}")
        frame[date_column] = pd.to_datetime(frame[date_column], errors="raise")
        frame = frame.set_index(date_column).sort_index()
        frame = frame.loc[(frame.index >= pd.Timestamp(start)) & (frame.index <= pd.Timestamp(end))]
        if frame.empty:
            raise ValueError(f"No rows in {self.path} for {start} through {end}")
        frame.columns = [str(column).title() for column in frame.columns]
        return validate_ohlcv(frame[["Open", "High", "Low", "Close", "Volume"]])
