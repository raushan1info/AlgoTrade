import json

import pandas as pd
import pytest

from config.loader import load_catalog, resolve_experiment
from data.providers.rest_json_provider import RestJSONMarketDataProvider


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_rest_json_provider_maps_api_records_and_expands_env(monkeypatch):
    from data.providers import rest_json_provider

    captured = {}
    payload = {
        "data": [
            {"timestamp": "2024-01-02", "open": 100, "high": 110, "low": 95,
             "close": 105, "volume": 1000},
            {"timestamp": "2024-01-03", "open": 105, "high": 112, "low": 101,
             "close": 109, "volume": 1200},
        ]
    }

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return FakeResponse(payload)

    monkeypatch.setenv("MARKET_DATA_API_TOKEN", "test-token")
    monkeypatch.setattr(rest_json_provider, "urlopen", fake_urlopen)
    provider = RestJSONMarketDataProvider({
        "url": "https://api.example.test/ohlcv",
        "query_params": {"symbol": "{symbol}", "from": "{start}", "to": "{end}"},
        "headers": {"Authorization": "Bearer env:MARKET_DATA_API_TOKEN"},
        "response_path": "data",
        "field_map": {
            "Date": "timestamp", "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume",
        },
    })

    frame = provider.get_history("RELIANCE", "2024-01-01", "2024-01-31")
    assert list(frame.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(frame) == 2
    assert frame["Close"].tolist() == [105, 109]
    assert "symbol=RELIANCE" in captured["url"]
    assert captured["authorization"] == "Bearer test-token"
    assert captured["timeout"] == 30


def test_rest_json_provider_fails_clearly_when_env_missing(monkeypatch):
    monkeypatch.delenv("MISSING_MARKET_TOKEN", raising=False)
    provider = RestJSONMarketDataProvider({
        "url": "https://api.example.test/ohlcv",
        "headers": {"Authorization": "Bearer env:MISSING_MARKET_TOKEN"},
    })
    with pytest.raises(ValueError, match="MISSING_MARKET_TOKEN"):
        provider.get_history("RELIANCE", "2024-01-01", "2024-01-31")


def test_catalog_rejects_unknown_dataset_provider():
    catalog = load_catalog()
    catalog["datasets"]["bad_dataset"] = {
        "provider": "missing_provider", "symbol": "TEST", "interval": "1d"
    }
    with pytest.raises(ValueError, match="unknown provider"):
        # load_catalog validates files; resolve validation is also expected to protect selected refs.
        from config.loader import validate_catalog
        validate_catalog(catalog)


def test_experiment_rejects_non_iso_dates():
    catalog = load_catalog()
    catalog["experiments"]["bad_dates"] = {
        "datasets": ["reliance_demo"], "strategies": ["ma_20_50"],
        "period": {"start": "01/01/2024", "end": "2024-12-31"},
    }
    with pytest.raises(ValueError, match="ISO format"):
        resolve_experiment(catalog, "bad_dates")
