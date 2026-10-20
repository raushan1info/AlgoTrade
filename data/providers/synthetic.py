"""Deterministic synthetic market data for offline demos and tests."""
import numpy as np
import pandas as pd

from core.base.models import validate_ohlcv
from core.market_data.base import MarketDataProvider


class SyntheticMarketDataProvider(MarketDataProvider):
    def get_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        dates = pd.bdate_range(start=start, end=end)
        if len(dates) < 2:
            raise ValueError("Date range must contain at least two business days")
        seed = sum(ord(char) for char in symbol) % (2**32 - 1)
        rng = np.random.default_rng(seed)
        daily_returns = rng.normal(loc=0.00035, scale=0.012, size=len(dates))
        close = 100 * np.cumprod(1 + daily_returns)
        open_price = np.r_[close[0], close[:-1]] * (1 + rng.normal(0, 0.003, len(dates)))
        high = np.maximum(open_price, close) * (1 + rng.uniform(0, 0.008, len(dates)))
        low = np.minimum(open_price, close) * (1 - rng.uniform(0, 0.008, len(dates)))
        volume = rng.integers(100_000, 2_000_000, len(dates))
        frame = pd.DataFrame(
            {"Open": open_price, "High": high, "Low": low, "Close": close, "Volume": volume},
            index=dates,
        )
        frame.index.name = "Date"
        return validate_ohlcv(frame)
