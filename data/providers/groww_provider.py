"""Groww historical candle adapter for cash and F&O instruments.

Uses the current /v1/historical/candles endpoint (not the deprecated candle/range endpoint).
This is a market-data adapter only and contains no order-placement functionality.
"""
from datetime import date, timedelta
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from core.base.models import validate_ohlcv
from core.market_data.base import MarketDataProvider


class GrowwMarketDataProvider(MarketDataProvider):
    """Read historical candles and derivative expiry/contract catalogs from Groww."""

    BASE_URL = "https://api.groww.in/v1"

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.token_env = self.config.get("token_env", "GROWW_ACCESS_TOKEN")
        self.exchange = str(self.config.get("exchange", "NSE")).upper()
        self.segment = str(self.config.get("segment", "CASH")).upper()
        self.candle_interval = str(self.config.get("candle_interval", "1day"))
        self.timeout_seconds = float(self.config.get("timeout_seconds", 30))
        self.base_url = str(self.config.get("base_url", self.BASE_URL)).rstrip("/")

    def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        token = os.environ.get(self.token_env, "").strip()
        if not token or token == "replace_me":
            raise RuntimeError(f"Set {self.token_env} in your root .env file.")
        query = urlencode({key: value for key, value in params.items() if value is not None})
        request = Request(
            f"{self.base_url}{path}?{query}",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "X-API-VERSION": str(self.config.get("api_version", "1.0")),
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"Groww API returned HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Could not connect to Groww API: {exc.reason}") from exc
        if not isinstance(payload, dict) or payload.get("status") == "FAILURE":
            raise RuntimeError(f"Groww API request failed: {payload!r}")
        return payload

    @staticmethod
    def _normalise_symbol(symbol: str, exchange: str) -> str:
        symbol = symbol.strip()
        if not symbol:
            raise ValueError("Groww symbol cannot be empty")
        if "-" in symbol and symbol.split("-", 1)[0].upper() in {"NSE", "BSE"}:
            return symbol
        if ":" in symbol:
            prefix, ticker = symbol.split(":", 1)
            return f"{prefix.upper()}-{ticker.upper()}"
        return f"{exchange.upper()}-{symbol.upper()}"

    @staticmethod
    def _parse_candles(candles: list[list[Any]]) -> pd.DataFrame:
        if not candles:
            raise ValueError("Groww returned no historical candles for the requested period.")
        rows = []
        for candle in candles:
            if len(candle) < 6:
                raise ValueError(f"Unexpected Groww candle shape: {candle!r}")
            timestamp = candle[0]
            if isinstance(timestamp, (int, float)):
                timestamp = pd.to_datetime(timestamp, unit="s")
            rows.append({
                "Date": pd.to_datetime(timestamp),
                "Open": candle[1],
                "High": candle[2],
                "Low": candle[3],
                "Close": candle[4],
                "Volume": candle[5],
            })
        frame = pd.DataFrame(rows).set_index("Date").sort_index()
        return validate_ohlcv(frame[["Open", "High", "Low", "Close", "Volume"]])

    def get_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        start_date, end_date = date.fromisoformat(start[:10]), date.fromisoformat(end[:10])
        if start_date > end_date:
            raise ValueError("start must be on or before end")
        groww_symbol = self._normalise_symbol(symbol, self.exchange)
        max_days = int(self.config.get("max_days_per_request", 175))
        if max_days < 1:
            raise ValueError("max_days_per_request must be positive")
        all_candles: list[list[Any]] = []
        cursor = start_date
        while cursor <= end_date:
            chunk_end = min(cursor + timedelta(days=max_days - 1), end_date)
            payload = self._get_json("/historical/candles", {
                "exchange": self.exchange,
                "segment": self.segment,
                "groww_symbol": groww_symbol,
                "start_time": f"{cursor.isoformat()} 00:00:00",
                "end_time": f"{chunk_end.isoformat()} 23:59:59",
                "candle_interval": self.candle_interval,
            })
            section = payload.get("payload", {})
            candles = section.get("candles", []) if isinstance(section, dict) else []
            all_candles.extend(candles)
            cursor = chunk_end + timedelta(days=1)
        frame = self._parse_candles(all_candles)
        frame = frame.loc[
            (frame.index >= pd.Timestamp(start_date))
            & (frame.index < pd.Timestamp(end_date) + pd.Timedelta(days=1))
        ]
        if frame.empty:
            raise ValueError(f"Groww returned no candles for {symbol!r} from {start} through {end}.")
        return validate_ohlcv(frame)

    def get_expiries(
        self, underlying_symbol: str, year: int | None = None, month: int | None = None
    ) -> list[date]:
        if self.segment != "FNO":
            raise ValueError("get_expiries requires provider segment: FNO")
        payload = self._get_json("/historical/expiries", {
            "exchange": self.exchange,
            "underlying_symbol": underlying_symbol.upper(),
            "year": year,
            "month": month,
        })
        values = payload.get("payload", {}).get("expiries", [])
        return [date.fromisoformat(value) for value in values]

    def get_contracts(self, underlying_symbol: str, expiry: date) -> list[str]:
        if self.segment != "FNO":
            raise ValueError("get_contracts requires provider segment: FNO")
        payload = self._get_json("/historical/contracts", {
            "exchange": self.exchange,
            "underlying_symbol": underlying_symbol.upper(),
            "expiry_date": expiry.isoformat(),
        })
        return list(payload.get("payload", {}).get("contracts", []))
