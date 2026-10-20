"""Market data provider interface."""
from abc import ABC, abstractmethod
import pandas as pd


class MarketDataProvider(ABC):
    @abstractmethod
    def get_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Return date-indexed OHLCV data."""
        raise NotImplementedError
