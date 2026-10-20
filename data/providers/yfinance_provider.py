"""Optional Yahoo Finance history provider."""
import pandas as pd
from core.base.models import validate_ohlcv
from core.market_data.base import MarketDataProvider


class YFinanceProvider(MarketDataProvider):
    def get_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError("Install Yahoo Finance support with pip install -e '.[market-data]'") from exc
        frame = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False, actions=False)
        if frame.empty:
            raise ValueError(f"No market data returned for {symbol!r}")
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)
        frame = frame.rename_axis("Date")
        return validate_ohlcv(frame[["Open", "High", "Low", "Close", "Volume"]])
