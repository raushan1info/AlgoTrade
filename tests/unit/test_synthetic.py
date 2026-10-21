from data.providers.synthetic import SyntheticMarketDataProvider


def test_synthetic_provider_returns_valid_ohlcv():
    data = SyntheticMarketDataProvider().get_history(
        "TEST.NS", "2023-01-01", "2023-06-30"
    )
    assert not data.empty
    assert {"Open", "High", "Low", "Close", "Volume"}.issubset(data.columns)
    assert data.index.is_monotonic_increasing
