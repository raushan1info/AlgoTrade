"""Zerodha Kite Connect historical OHLCV adapter.

This adapter is read-only: it fetches history and instrument metadata but never places orders.
Kite access tokens are short-lived and normally need to be refreshed each trading day.
"""
from datetime import date, datetime, timedelta
import os
from pathlib import Path
from typing import Any

import pandas as pd

from core.base.models import validate_ohlcv
from core.market_data.base import MarketDataProvider


class KiteConnectMarketDataProvider(MarketDataProvider):
    """Fetch daily historical candles using the official kiteconnect Python SDK."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.api_key_env = self.config.get("api_key_env", "KITE_API_KEY")
        self.access_token_env = self.config.get("access_token_env", "KITE_ACCESS_TOKEN")
        self.instrument_cache_dir = Path(self.config.get("instrument_cache_dir", "data/cache/instruments"))
        self._kite = None

    def _client(self):
        api_key = os.environ.get(self.api_key_env, "").strip()
        access_token = os.environ.get(self.access_token_env, "").strip()
        if not api_key or api_key == "replace_me":
            raise RuntimeError(f"Set {self.api_key_env} in your root .env file.")
        if not access_token or access_token == "replace_me":
            raise RuntimeError(
                f"Set {self.access_token_env} in your root .env file. "
                "Kite access tokens usually expire before the next trading day."
            )
        try:
            from kiteconnect import KiteConnect
        except ImportError as exc:
            raise RuntimeError("Install the optional dependency with pip install -e '.[zerodha]'") from exc
        if self._kite is None:
            kite = KiteConnect(api_key=api_key)
            kite.set_access_token(access_token)
            self._kite = kite
        return self._kite

    def _resolve_token(self, symbol: str) -> int:
        if str(symbol).strip().isdigit():
            return int(symbol)
        if ":" not in symbol:
            raise ValueError(
                "Kite symbols must be an instrument token or EXCHANGE:TRADING_SYMBOL "
                "(for example NSE:RELIANCE)."
            )
        exchange, trading_symbol = (part.strip().upper() for part in symbol.split(":", 1))
        if not exchange or not trading_symbol:
            raise ValueError("Kite symbol must be EXCHANGE:TRADING_SYMBOL.")
        cache_dir = self.instrument_cache_dir
        if not cache_dir.is_absolute():
            cache_dir = Path(__file__).resolve().parents[2] / cache_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"kite_instruments_{exchange}_{date.today().isoformat()}.csv"
        if cache_file.is_file():
            instruments = pd.read_csv(cache_file)
        else:
            instruments = pd.DataFrame(self._client().instruments(exchange))
            if instruments.empty:
                raise ValueError(f"Kite returned an empty instrument master for {exchange}.")
            temporary = cache_file.with_suffix(".tmp")
            instruments.to_csv(temporary, index=False)
            temporary.replace(cache_file)
        matches = instruments.loc[
            instruments["tradingsymbol"].astype(str).str.upper().eq(trading_symbol)
        ]
        if matches.empty:
            raise ValueError(
                f"Could not resolve {symbol!r} in today's Kite instrument master. "
                "Check exchange/symbol or use the numeric instrument_token."
            )
        if len(matches) > 1:
            raise ValueError(f"Instrument symbol {symbol!r} is ambiguous; use its numeric token.")
        return int(matches.iloc[0]["instrument_token"])

    @staticmethod
    def _datetime(value: str, *, end: bool = False) -> datetime:
        parsed = datetime.fromisoformat(value)
        if len(value) == 10 and end:
            return parsed.replace(hour=23, minute=59, second=59)
        return parsed

    def get_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        start_date = date.fromisoformat(start[:10])
        end_date = date.fromisoformat(end[:10])
        if start_date > end_date:
            raise ValueError("start must be on or before end")
        kite = self._client()
        token = self._resolve_token(symbol)
        records: list[dict[str, Any]] = []
        cursor = start_date
        while cursor <= end_date:
            chunk_end = min(cursor + timedelta(days=364), end_date)
            records.extend(kite.historical_data(
                token,
                self._datetime(cursor.isoformat()),
                self._datetime(chunk_end.isoformat(), end=True),
                self.config.get("kite_interval", "day"),
                continuous=False,
                oi=bool(self.config.get("include_oi", False)),
            ))
            cursor = chunk_end + timedelta(days=1)
        if not records:
            raise ValueError(f"Kite returned no candles for {symbol!r} from {start} through {end}.")
        frame = pd.DataFrame(records).rename(columns={
            "date": "Date", "open": "Open", "high": "High", "low": "Low",
            "close": "Close", "volume": "Volume",
        })
        frame = frame.set_index("Date")
        return validate_ohlcv(frame[["Open", "High", "Low", "Close", "Volume"]])
