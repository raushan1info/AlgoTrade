"""Configurable REST/JSON OHLCV provider.

Supports a single GET request returning a JSON list of candle objects (or a list
nested at response_path). Authentication values are resolved from environment
variables; provider-specific flows, pagination, and response schemas may need
a dedicated adapter.
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

import pandas as pd

from core.configuration.environment import load_environment
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
        self.auth = config.get("auth", {})
        if self.auth:
            if not isinstance(self.auth, dict):
                raise ValueError("REST JSON provider auth must be a mapping")
            auth_type = self.auth.get("type")
            if auth_type not in {"bearer", "api_key_header"}:
                raise ValueError("auth.type must be 'bearer' or 'api_key_header'")
            if not self.auth.get("token_env"):
                raise ValueError("auth.token_env must name an environment variable")
            if auth_type == "api_key_header" and not self.auth.get("header_name"):
                raise ValueError("auth.header_name is required for api_key_header authentication")
        self.response_path = config.get("response_path", "")
        self.field_map = config.get("field_map", DEFAULT_FIELD_MAP)
        self.timeout = float(config.get("timeout_seconds", 30))
        if self.timeout <= 0:
            raise ValueError("timeout_seconds must be positive")
        required = {"Date", "Open", "High", "Low", "Close", "Volume"}
        if not isinstance(self.field_map, dict) or not required.issubset(self.field_map):
            raise ValueError("field_map must map Date, Open, High, Low, Close, and Volume")

    def _build_headers(self) -> dict[str, str]:
        # Loading is safe to call repeatedly; OS/CI variables override .env values.
        load_environment()
        headers = {str(key): str(value) for key, value in self.headers.items()}
        if self.auth:
            env_name = self.auth["token_env"]
            token = os.environ.get(env_name)
            if not token:
                raise ValueError(
                    f"Authentication requires environment variable '{env_name}' "
                    "(set it in the root .env file or the process environment)"
                )
            if self.auth["type"] == "bearer":
                headers["Authorization"] = f"Bearer {token}"
            else:
                headers[self.auth["header_name"]] = token
        headers.setdefault("Accept", "application/json")
        return headers

    def get_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        context = {"symbol": symbol, "start": start, "end": end}
        params = {
            str(key): value.format_map(context) if isinstance(value, str) else value
            for key, value in self.query_params.items()
        }
        url = self.url
        if params:
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{urlencode(params)}"
        request = Request(url, headers=self._build_headers(), method="GET")
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
                raise ValueError(
                    f"API response does not contain response_path '{self.response_path}'"
                )
            payload = payload[key]
        if not isinstance(payload, list) or not payload:
            raise ValueError("API response must resolve to a non-empty list of OHLCV records")
        if not all(isinstance(row, dict) for row in payload):
            raise ValueError("Each API candle must be a JSON object")

        missing = set(self.field_map.values()) - set(payload[0])
        if missing:
            raise ValueError(
                f"API candle is missing configured source fields: {sorted(missing)}"
            )
        frame = pd.DataFrame(
            {output: [row[source] for row in payload] for output, source in self.field_map.items()}
        )
        frame["Date"] = pd.to_datetime(frame["Date"], errors="raise")
        frame = frame.set_index("Date").sort_index()
        frame = frame.loc[
            (frame.index >= pd.Timestamp(start)) & (frame.index <= pd.Timestamp(end))
        ]
        if frame.empty:
            raise ValueError(
                f"API returned no candles for {symbol!r} from {start} through {end}"
            )
        return validate_ohlcv(frame[["Open", "High", "Low", "Close", "Volume"]])
