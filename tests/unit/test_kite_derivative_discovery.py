from datetime import date

import pandas as pd

from core.base.derivatives import DerivativeContract
from data.providers.kite_provider import KiteConnectMarketDataProvider


def _derivative_master():
    return pd.DataFrame({
        "instrument_token": [100, 101, 102, 103, 104],
        "tradingsymbol": [
            "NIFTY26NOVFUT", "NIFTY26NOV25000CE", "NIFTY26NOV25000PE",
            "NIFTY26OCTFUT", "BANKNIFTY26NOVFUT",
        ],
        "name": ["NIFTY", "NIFTY", "NIFTY", "NIFTY", "BANKNIFTY"],
        "expiry": ["2026-11-26", "2026-11-26", "2026-11-26", "2026-10-29", "2026-11-25"],
        "instrument_type": ["FUT", "CE", "PE", "FUT", "FUT"],
        "segment": ["NFO-FUT", "NFO-OPT", "NFO-OPT", "NFO-FUT", "NFO-FUT"],
        "lot_size": [65, 65, 65, 65, 30],
        "tick_size": [0.05, 0.05, 0.05, 0.05, 0.05],
        "strike": [0, 25000, 25000, 0, 0],
    })


def test_kite_derivative_discovery_returns_future_and_options_for_underlying():
    provider = KiteConnectMarketDataProvider({"instrument_cache_dir": "unused"})
    provider._instrument_master = lambda exchange: _derivative_master()

    contracts = provider.list_derivative_contracts(
        "NIFTY 50", date(2026, 10, 25), exchanges=("NFO",)
    )

    assert len(contracts) == 3
    assert {contract.kind for contract in contracts} == {"future", "option"}
    assert {contract.instrument_id for contract in contracts} == {"100", "101", "102"}
    call = next(contract for contract in contracts if contract.option_type == "CE")
    assert call.strike == 25000
    assert call.lot_size == 65
    assert call.tick_size == 0.05
    assert call.expiry == date(2026, 11, 26)


def test_kite_derivative_discovery_filters_other_underlyings_and_expired_contracts():
    provider = KiteConnectMarketDataProvider({"instrument_cache_dir": "unused"})
    provider._instrument_master = lambda exchange: _derivative_master()

    contracts = provider.list_derivative_contracts(
        "NIFTY", date(2026, 10, 30), exchanges=("NFO",)
    )

    assert {contract.instrument_id for contract in contracts} == {"100", "101", "102"}


def test_kite_contract_history_uses_contract_instrument_token():
    provider = KiteConnectMarketDataProvider({"instrument_cache_dir": "unused"})
    provider.get_history = lambda symbol, start, end: pd.DataFrame({"symbol": [symbol]})
    exact_contract = DerivativeContract(
        instrument_id="12345",
        underlying="NIFTY",
        exchange="NFO",
        segment="NFO-OPT",
        expiry=date(2026, 11, 26),
        lot_size=65,
        tick_size=0.05,
        kind="option",
        strike=25000,
        option_type="CE",
    )
    result = provider.get_contract_history(exact_contract, "2026-10-25", "2026-10-26")
    assert result.iloc[0]["symbol"] == "12345"
