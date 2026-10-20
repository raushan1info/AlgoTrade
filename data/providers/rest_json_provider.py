"""Configurable REST/JSON OHLCV provider.

Supports a single GET request returning a JSON list of candle objects (or a list
nested at response_path). Provider-specific authentication, pagination, and
response schemas may require a dedicated adapter.
"""
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

import pandas as pd

from core.base.models import validate_ohlcv
from core.market_data.base import MarketDataProvider

DEFAULT_FIELD_MAP = {
    "Date": "date",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
}


def _resolve_env(value: str) -> str:
    """Expand env:NAME references without exposing secret values in errors."""
    def replace(match):
        name = match.group(1)
        resolved = os.environ.get(name)
        if not resolved:
            raise ValueError(f"Required environment variable '{name}' is not set")
        return resolved

    return re.sub(r"env:([A-Za-z_][A-Za-z0-9_]*)", replace, value)


def _format_template(value, context: dict[str, str]):
    if not isinstance(value, str):
        return value
    try:
        return value.format_map(context)
    except KeyError as exc:
        raise ValueError(f"Unknown template field in provider configuration: {exc}") from exc


class RestJSONMarketDataProvider(MarketDataProvider):
    """Fetch OHLCV records from a configurable REST endpoint."""

    def __init__(self, config: dict):
        self.url = config.get("url")
        if not self.url:
            raise ValueError("REST JSON provider requires 'url'")
        parsed = urlsplit(self.url)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise ValueError("REST JSON provider url must be an absolute HTTP(S) URL")
        self.query_params = config.get("query_params", {})
        self.headers = config.get("headers", {})
        self.response_path = config.get("response_path", "")
        self.field_map = config.get("field_map", DEFAULT_FIELD_MAP)
        self.timeout = float(config.get("timeout_seconds", 30))
        if self.timeout <= 0:
            raise ValueError("timeout_seconds must be positive")
        required = {"Date", "Open", "High", "Low", "Close", "Volume"}
        if not isinstance(self.field_map, dict) or not required.issubset(self.field_map):
            raise ValueError("field_map must map Date, Open, High, Low, Close, and Volume")

    def get_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        context = {"symbol": symbol, "start": start, "end": end}
        params = {
            str(key): _format_template(value, context)
            for key, value in self.query_params.items()
        }
        url = self.url
        if params:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode(params)}"
        headers = {str(key): _resolve_env(str(value)) for key, value in self.headers.items()}
        headers.setdefault("Accept", "application/json")
        request = Request(url, headers=headers, method="GET")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"Market-data API returned HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"Unable to reach market-data API: {exc.reason}") from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Market-data API did not return valid UTF-8 JSON") from exc

        for key in filter(None, str(self.response_path).split(".")):
            if not isinstance(payload, dict) or key not in payload:
                raise ValueError(f"API response does not contain response_path '{self.response_path}'")
            payload = payload[key]
        if not isinstance(payload, list) or not payload:
            raise ValueError("API response must resolve to a non-empty list of OHLCV records")
        if not all(isinstance(row, dict) for row in payload):
            raise ValueError("Each API candle must be a JSON object")

        missing = set(self.field_map.values()) - set(payload[0])
        if missing:
            raise ValueError(f"API candle is missing configured source fields: {sorted(missing)}")
        frame = pd.DataFrame(
            {output: [row[source] for row in payload] for output, source in self.field_map.items()}
        )
        frame["Date"] = pd.to_datetime(frame["Date"], errors="raise")
        frame = frame.set_index("Date").sort_index()
        frame = frame.loc[(frame.index >= pd.Timestamp(start)) & (frame.index <= pd.Timestamp(end))]
        if frame.empty:
            raise ValueError(f"API returned no candles for {symbol!r} from {start} through {end}")
        return validate_ohlcv(frame[["Open", "High", "Low", "Close", "Volume"]])
