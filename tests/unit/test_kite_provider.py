import pandas as pd

from data.providers.kite_provider import KiteConnectMarketDataProvider


def test_kite_index_discovery_filters_to_nifty_and_sensex_indices():
    provider = KiteConnectMarketDataProvider({"instrument_cache_dir": "unused"})
    masters = {
        "NSE": pd.DataFrame({
            "instrument_token": [1, 2, 3, 4],
            "tradingsymbol": ["NIFTY 50", "NIFTY BANK", "RELIANCE", "NIFTY FUT"],
            "name": ["NIFTY 50", "NIFTY BANK", "RELIANCE", "NIFTY FUT"],
            "segment": ["INDICES", "INDICES", "NSE", "NFO"],
            "instrument_type": ["EQ", "EQ", "EQ", "FUT"],
        }),
        "BSE": pd.DataFrame({
            "instrument_token": [10, 11],
            "tradingsymbol": ["SENSEX", "SENSEX FUT"],
            "name": ["SENSEX", "SENSEX FUT"],
            "segment": ["INDICES", "BFO"],
            "instrument_type": ["EQ", "FUT"],
        }),
    }
    provider._instrument_master = lambda exchange: masters[exchange]

    found = provider.list_index_instruments(("NSE", "BSE"), ("NIFTY", "SENSEX"))

    assert set(found["tradingsymbol"]) == {"NIFTY 50", "NIFTY BANK", "SENSEX"}
    assert set(found["exchange"]) == {"NSE", "BSE"}
    assert set(found["instrument_token"]) == {1, 2, 10}
