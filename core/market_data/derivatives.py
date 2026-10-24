"""Interfaces for derivative contract metadata and market data.

These interfaces intentionally do not implement exchange or broker access. A concrete
adapter must respect provider licensing, authentication, rate limits, and historical
contract availability.
"""
from abc import ABC, abstractmethod
from datetime import date
import pandas as pd
from core.base.derivatives import DerivativeContract


class DerivativeContractProvider(ABC):
    @abstractmethod
    def list_contracts(self, underlying: str, as_of: date) -> list[DerivativeContract]:
        """Return contracts valid for the requested as-of date from an instrument master."""
        raise NotImplementedError


class DerivativeMarketDataProvider(ABC):
    @abstractmethod
    def get_contract_history(
        self, contract: DerivativeContract, start: str, end: str
    ) -> pd.DataFrame:
        """Return date-indexed OHLCV history for one exact derivative contract."""
        raise NotImplementedError
