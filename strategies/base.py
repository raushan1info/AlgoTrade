"""Common strategy contract."""
from abc import ABC, abstractmethod
import pandas as pd


class BaseStrategy(ABC):
    """A strategy turns normalized OHLCV data into a position signal."""

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """Return a DataFrame containing a numeric signal column in [0, 1]."""
        raise NotImplementedError
