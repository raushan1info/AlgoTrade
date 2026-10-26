from datetime import date

import pytest

from core.base.derivatives import DerivativeContract, Instrument


def test_supported_index_instrument_is_valid():
    instrument = Instrument(
        instrument_id="nifty50", exchange="NSE", segment="index",
        symbol="NIFTY 50", kind="index",
    )
    assert instrument.exchange == "NSE"


def test_option_contract_requires_strike_and_option_type():
    with pytest.raises(ValueError, match="positive strike"):
        DerivativeContract(
            instrument_id="NIFTY-OPTION", underlying="NIFTY 50", exchange="NSE",
            segment="OPTIDX", expiry=date(2026, 11, 24), lot_size=1, tick_size=0.05,
            kind="option",
        )


def test_derivative_contract_rejects_invalid_lot_size():
    with pytest.raises(ValueError, match="lot_size"):
        DerivativeContract(
            instrument_id="NIFTY-FUT", underlying="NIFTY 50", exchange="NSE",
            segment="FUTIDX", expiry=date(2026, 11, 24), lot_size=0, tick_size=0.05,
            kind="future",
        )


def test_option_contract_requires_valid_option_type():
    with pytest.raises(ValueError, match="option_type"):
        DerivativeContract(
            instrument_id="NIFTY-OPTION", underlying="NIFTY 50", exchange="NSE",
            segment="OPTIDX", expiry=date(2026, 11, 24), lot_size=1, tick_size=0.05,
            kind="option", strike=25000, option_type="CALL",
        )
