"""Offline unit tests for Groww response parsing and symbol normalization."""
import pytest

from data.providers.groww_provider import GrowwMarketDataProvider


def test_normalise_groww_symbols():
    assert GrowwMarketDataProvider._normalise_symbol("RELIANCE", "NSE") == "NSE-RELIANCE"
    assert GrowwMarketDataProvider._normalise_symbol("NSE:RELIANCE", "NSE") == "NSE-RELIANCE"
    assert GrowwMarketDataProvider._normalise_symbol("BSE-SENSEX", "NSE") == "BSE-SENSEX"


def test_parse_groww_candles_accepts_iso_timestamp_and_validates_ohlcv():
    frame = GrowwMarketDataProvider._parse_candles([
        ["2025-01-02T00:00:00", 100, 105, 99, 103, 1000, None],
        ["2025-01-03T00:00:00", 103, 106, 102, 105, 1200, None],
    ])
    assert list(frame.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert len(frame) == 2
    assert frame["Close"].tolist() == [103, 105]


def test_parse_groww_candles_rejects_invalid_rows():
    with pytest.raises(ValueError, match="High"):
        GrowwMarketDataProvider._parse_candles([
            ["2025-01-02T00:00:00", 100, 98, 99, 101, 1000]
        ])


def test_parse_groww_candles_rejects_empty_response():
    with pytest.raises(ValueError, match="no historical candles"):
        GrowwMarketDataProvider._parse_candles([])


def test_groww_missing_token_fails_before_network(monkeypatch):
    monkeypatch.delenv("TEST_GROWW_TOKEN", raising=False)
    provider = GrowwMarketDataProvider({"token_env": "TEST_GROWW_TOKEN"})
    with pytest.raises(RuntimeError, match="TEST_GROWW_TOKEN"):
        provider.get_expiries("NIFTY", year=2025)
