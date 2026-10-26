"""Optional Yahoo Finance daily history provider."""
from datetime import date, datetime, timedelta

import pandas as pd
from core.base.models import validate_ohlcv
from core.market_data.base import MarketDataProvider


class YFinanceProvider(MarketDataProvider):
    def get_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError("Install Yahoo Finance support with pip install -e '.[market-data]'") from exc
        # yfinance's end parameter is exclusive; our provider contract is inclusive.
        end_date = date.fromisoformat(end) if len(end) == 10 else datetime.fromisoformat(end).date()
        exclusive_end = (end_date + timedelta(days=1)).isoformat()
        frame = yf.download(
            symbol, start=start, end=exclusive_end, auto_adjust=True,
            progress=False, actions=False, group_by="column"
        )
        if frame.empty:
            raise ValueError(f"No market data returned for {symbol!r} from {start} through {end}")
        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)
        frame = frame.rename_axis("Date")
        return validate_ohlcv(frame[["Open", "High", "Low", "Close", "Volume"]])
