from datetime import date

import pytest

from core.base.derivatives import DerivativeContract
from core.market_data.contract_selection import select_contracts


AS_OF = date(2026, 10, 25)


def _contract(
    token: str,
    *,
    expiry: date = date(2026, 11, 5),
    kind: str = "option",
    strike: float | None = 25000,
    option_type: str | None = "CE",
    underlying: str = "NIFTY",
    lot_size: int = 65,
) -> DerivativeContract:
    return DerivativeContract(
        instrument_id=token,
        underlying=underlying,
        exchange="NFO",
        segment="NFO-OPT" if kind == "option" else "NFO-FUT",
        expiry=expiry,
        lot_size=lot_size,
        tick_size=0.05,
        kind=kind,
        strike=strike,
        option_type=option_type,
    )


def _policy(**overrides):
    return {
        "kind": "option",
        "min_days_to_expiry": 2,
        "max_days_to_expiry": 45,
        "max_moneyness_pct": 3.0,
        "max_candidates": 1,
        "signal_option_type": {"LONG": "CE"},
        **overrides,
    }


def test_selects_nearest_expiry_and_nearest_atm_call_deterministically():
    contracts = [
        _contract("far-atm", expiry=date(2026, 11, 26), strike=25000),
        _contract("near-otm", expiry=date(2026, 11, 5), strike=25200),
        _contract("near-atm", expiry=date(2026, 11, 5), strike=25000),
        _contract("near-put", expiry=date(2026, 11, 5), strike=25000, option_type="PE"),
    ]

    result = select_contracts(
        contracts,
        underlying="NIFTY",
        as_of=AS_OF,
        spot_price=25010,
        signal_state="LONG",
        policy=_policy(),
    )

    assert [item["instrument_id"] for item in result] == ["near-atm"]
    assert result[0]["days_to_expiry"] == 11
    assert result[0]["lot_size"] == 65
    assert result[0]["liquidity_status"] == "UNKNOWN_NOT_PROVIDED"
    assert result[0]["research_only"] is True


def test_excludes_expired_too_near_and_too_far_contracts():
    contracts = [
        _contract("expired", expiry=date(2026, 10, 24)),
        _contract("tomorrow", expiry=date(2026, 10, 26)),
        _contract("too-far", expiry=date(2027, 1, 15)),
    ]

    result = select_contracts(
        contracts,
        underlying="NIFTY",
        as_of=AS_OF,
        spot_price=25000,
        signal_state="LONG",
        policy=_policy(),
    )

    assert result == []


def test_rejects_contracts_outside_moneyness_and_wrong_underlying():
    contracts = [
        _contract("too-far-strike", strike=26000),
        _contract("other-underlying", underlying="BANKNIFTY", strike=25000),
    ]

    result = select_contracts(
        contracts,
        underlying="NIFTY",
        as_of=AS_OF,
        spot_price=25000,
        signal_state="LONG",
        policy=_policy(max_moneyness_pct=2.0),
    )

    assert result == []


def test_flat_signal_does_not_select_contract_unless_explicitly_allowed():
    contracts = [_contract("call"), _contract("put", option_type="PE")]

    assert select_contracts(
        contracts, underlying="NIFTY", as_of=AS_OF, spot_price=25000,
        signal_state="FLAT", policy=_policy(),
    ) == []

    result = select_contracts(
        contracts,
        underlying="NIFTY",
        as_of=AS_OF,
        spot_price=25000,
        signal_state="FLAT",
        policy=_policy(allow_flat_signal=True, signal_option_type={"FLAT": "PE"}),
    )
    assert [item["instrument_id"] for item in result] == ["put"]


def test_future_policy_selects_nearest_eligible_future():
    contracts = [
        _contract("far-future", expiry=date(2026, 11, 26), kind="future", strike=None, option_type=None),
        _contract("near-future", expiry=date(2026, 11, 5), kind="future", strike=None, option_type=None),
    ]

    result = select_contracts(
        contracts,
        underlying="NIFTY",
        as_of=AS_OF,
        spot_price=25000,
        signal_state="LONG",
        policy={"kind": "future", "min_days_to_expiry": 2, "max_days_to_expiry": 45},
    )

    assert [item["instrument_id"] for item in result] == ["near-future"]
    assert result[0]["strike"] is None


@pytest.mark.parametrize("spot", [0, -1])
def test_rejects_non_positive_spot(spot):
    with pytest.raises(ValueError, match="spot_price must be positive"):
        select_contracts(
            [_contract("call")],
            underlying="NIFTY",
            as_of=AS_OF,
            spot_price=spot,
            signal_state="LONG",
            policy=_policy(),
        )
