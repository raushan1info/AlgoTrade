from data.providers.rest_json_provider import RestJSONMarketDataProvider


def _provider(auth):
    return RestJSONMarketDataProvider({
        "url": "https://api.example.com/v1/ohlcv",
        "auth": auth,
        "field_map": {
            "Date": "timestamp",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        },
    })


def test_bearer_auth_reads_token_from_environment(monkeypatch):
    monkeypatch.setenv("ALGOTRADE_TEST_MARKET_TOKEN", "test-token-value")
    provider = _provider({
        "type": "bearer",
        "token_env": "ALGOTRADE_TEST_MARKET_TOKEN",
    })
    headers = provider._build_headers()
    assert headers["Authorization"] == "Bearer test-token-value"
    assert headers["Accept"] == "application/json"


def test_api_key_header_reads_token_from_environment(monkeypatch):
    monkeypatch.setenv("ALGOTRADE_TEST_API_KEY", "test-api-key")
    provider = _provider({
        "type": "api_key_header",
        "header_name": "X-API-Key",
        "token_env": "ALGOTRADE_TEST_API_KEY",
    })
    assert provider._build_headers()["X-API-Key"] == "test-api-key"


def test_missing_auth_environment_variable_has_actionable_error(monkeypatch):
    monkeypatch.delenv("ALGOTRADE_UNSET_TEST_TOKEN", raising=False)
    provider = _provider({
        "type": "bearer",
        "token_env": "ALGOTRADE_UNSET_TEST_TOKEN",
    })
    try:
        provider._build_headers()
    except ValueError as exc:
        assert "ALGOTRADE_UNSET_TEST_TOKEN" in str(exc)
        assert "root .env" in str(exc)
    else:
        raise AssertionError("Expected missing environment variable to raise ValueError")
