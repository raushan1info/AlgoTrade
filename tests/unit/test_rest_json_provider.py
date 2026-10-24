import json

import pytest

from data.providers import rest_json_provider
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


def _provider(auth=None):
    config = {
        "url": "https://api.example.test/ohlcv",
        "query_params": {"symbol": "{symbol}", "from": "{start}", "to": "{end}"},
        "response_path": "data",
        "field_map": {
            "Date": "timestamp",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        },
    }
    if auth is not None:
        config["auth"] = auth
    return RestJSONMarketDataProvider(config)


def test_rest_json_provider_maps_api_records(monkeypatch):
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

    monkeypatch.setenv("ALGOTRADE_TEST_PROVIDER_TOKEN", "test-token")
    monkeypatch.setattr(rest_json_provider, "urlopen", fake_urlopen)
    provider = _provider({
        "type": "bearer",
        "token_env": "ALGOTRADE_TEST_PROVIDER_TOKEN",
    })

    frame = provider.get_history("RELIANCE", "2024-01-01", "2024-01-31")
    assert list(frame.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(frame) == 2
    assert frame["Close"].tolist() == [105, 109]
    assert "symbol=RELIANCE" in captured["url"]
    assert captured["authorization"] == "Bearer test-token"
    assert captured["timeout"] == 30


def test_api_key_header_auth_uses_environment_variable(monkeypatch):
    monkeypatch.setenv("ALGOTRADE_TEST_API_KEY", "test-api-key")
    provider = _provider({
        "type": "api_key_header",
        "header_name": "X-API-Key",
        "token_env": "ALGOTRADE_TEST_API_KEY",
    })
    assert provider._build_headers()["X-API-Key"] == "test-api-key"


def test_missing_auth_environment_variable_fails_clearly(monkeypatch):
    monkeypatch.delenv("ALGOTRADE_TEST_MISSING_TOKEN", raising=False)
    provider = _provider({
        "type": "bearer",
        "token_env": "ALGOTRADE_TEST_MISSING_TOKEN",
    })
    with pytest.raises(ValueError, match="ALGOTRADE_TEST_MISSING_TOKEN"):
        provider._build_headers()
