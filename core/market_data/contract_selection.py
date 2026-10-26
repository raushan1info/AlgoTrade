"""Deterministic, provider-independent F&O contract selection policies.

Selection is for research candidates only. Missing liquidity data is surfaced as unknown,
never treated as a pass or fabricated value.
"""
from datetime import date
from math import isfinite
from typing import Any, Iterable

from core.base.derivatives import DerivativeContract


def select_contracts(
    contracts: Iterable[DerivativeContract],
    *,
    underlying: str,
    as_of: date,
    spot_price: float,
    signal_state: str,
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    """Select contracts deterministically from a provider-supplied dated contract list."""
    if not isfinite(float(spot_price)) or spot_price <= 0:
        raise ValueError("spot_price must be a finite positive number")
    if not underlying.strip():
        raise ValueError("underlying must be non-empty")
    kind = str(policy.get("kind", "option")).lower()
    if kind not in {"future", "option"}:
        raise ValueError("policy.kind must be 'future' or 'option'")
    min_dte = int(policy.get("min_days_to_expiry", 2))
    max_dte = int(policy.get("max_days_to_expiry", 45))
    if min_dte < 0 or max_dte < min_dte:
        raise ValueError("Expiry bounds must satisfy 0 <= min_days_to_expiry <= max_days_to_expiry")
    if signal_state not in {"LONG", "FLAT"}:
        raise ValueError("signal_state must be LONG or FLAT")
    if signal_state == "FLAT" and not bool(policy.get("allow_flat_signal", False)):
        return []

    option_map = policy.get("signal_option_type", {"LONG": "CE", "FLAT": "PE"})
    option_type = str(option_map.get(signal_state, "")).upper() if kind == "option" else None
    if kind == "option" and option_type not in {"CE", "PE"}:
        raise ValueError(f"No valid option type configured for signal state {signal_state!r}")
    max_moneyness_pct = float(policy.get("max_moneyness_pct", 3.0))
    if not isfinite(max_moneyness_pct) or max_moneyness_pct < 0:
        raise ValueError("max_moneyness_pct must be finite and non-negative")
    max_candidates = int(policy.get("max_candidates", 1))
    if max_candidates < 1:
        raise ValueError("max_candidates must be at least 1")

    eligible: list[tuple[DerivativeContract, int]] = []
    for contract in contracts:
        if contract.underlying.upper() != underlying.upper() or contract.kind != kind:
            continue
        dte = (contract.expiry - as_of).days
        if dte < min_dte or dte > max_dte:
            continue
        if contract.valid_from and as_of < contract.valid_from:
            continue
        if contract.valid_to and as_of > contract.valid_to:
            continue
        if kind == "option":
            if contract.option_type != option_type or contract.strike is None:
                continue
            moneyness_pct = abs(contract.strike / spot_price - 1.0) * 100.0
            if moneyness_pct > max_moneyness_pct:
                continue
        eligible.append((contract, dte))

    if not eligible:
        return []

    nearest_expiry = min(dte for _, dte in eligible)
    expiry_candidates = [(contract, dte) for contract, dte in eligible if dte == nearest_expiry]
    if kind == "future":
        chosen = sorted(expiry_candidates, key=lambda item: (item[0].expiry, item[0].exchange,
                                                              item[0].instrument_id))[:1]
    else:
        chosen = sorted(
            expiry_candidates,
            key=lambda item: (
                abs(float(item[0].strike) / spot_price - 1.0),
                item[0].strike,
                item[0].exchange,
                item[0].instrument_id,
            ),
        )[:max_candidates]
    output: list[dict[str, Any]] = []
    for contract, dte in chosen:
        output.append({
            "instrument_id": contract.instrument_id,
            "underlying": contract.underlying,
            "exchange": contract.exchange,
            "segment": contract.segment,
            "expiry": contract.expiry.isoformat(),
            "days_to_expiry": dte,
            "kind": contract.kind,
            "strike": contract.strike,
            "option_type": contract.option_type,
            "lot_size": contract.lot_size,
            "tick_size": contract.tick_size,
            "spot_price": float(spot_price),
            "moneyness_pct": (
                round((float(contract.strike) / spot_price - 1.0) * 100.0, 4)
                if contract.strike is not None else None
            ),
            "liquidity_status": "UNKNOWN_NOT_PROVIDED",
            "selection_reason": (
                f"Nearest eligible expiry ({dte} calendar days); closest configured "
                f"{option_type} strike to spot within {max_moneyness_pct:.2f}% moneyness"
                if kind == "option" else f"Nearest eligible futures expiry ({dte} calendar days)"
            ),
            "research_only": True,
        })
    return output
