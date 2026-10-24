"""Provider-independent instrument and derivative contract models.

Contract metadata must come from a dated, authoritative instrument master. Do not
hard-code lot sizes or assume they remain constant across expiry dates.
"""
from dataclasses import dataclass
from datetime import date
from typing import Literal

InstrumentKind = Literal["index", "equity", "future", "option"]
OptionType = Literal["CE", "PE"]


@dataclass(frozen=True)
class Instrument:
    instrument_id: str
    exchange: str
    segment: str
    symbol: str
    kind: InstrumentKind
    underlying: str | None = None
    currency: str = "INR"

    def __post_init__(self) -> None:
        if not all((self.instrument_id, self.exchange, self.segment, self.symbol)):
            raise ValueError("instrument_id, exchange, segment, and symbol are required")
        if self.kind not in {"index", "equity", "future", "option"}:
            raise ValueError(f"Unsupported instrument kind: {self.kind}")
        if self.kind in {"future", "option"} and not self.underlying:
            raise ValueError("Derivative instruments must define an underlying")


@dataclass(frozen=True)
class DerivativeContract:
    instrument_id: str
    underlying: str
    exchange: str
    segment: str
    expiry: date
    lot_size: int
    tick_size: float
    kind: Literal["future", "option"]
    strike: float | None = None
    option_type: OptionType | None = None
    valid_from: date | None = None
    valid_to: date | None = None

    def __post_init__(self) -> None:
        if not self.instrument_id or not self.underlying or not self.exchange or not self.segment:
            raise ValueError("Contract identity, underlying, exchange, and segment are required")
        if self.lot_size <= 0:
            raise ValueError("lot_size must be positive")
        if self.tick_size <= 0:
            raise ValueError("tick_size must be positive")
        if self.kind not in {"future", "option"}:
            raise ValueError("kind must be 'future' or 'option'")
        if self.kind == "option":
            if self.strike is None or self.strike <= 0:
                raise ValueError("Options require a positive strike")
            if self.option_type not in {"CE", "PE"}:
                raise ValueError("Options require option_type 'CE' or 'PE'")
        elif self.strike is not None or self.option_type is not None:
            raise ValueError("Futures must not define strike or option_type")
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError("valid_from must be <= valid_to")
