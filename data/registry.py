"""Factory for configured market-data providers."""
from typing import Any
from core.market_data.base import MarketDataProvider
from data.providers.synthetic import SyntheticMarketDataProvider


def create_provider(provider_id: str, provider_config: dict[str, Any]) -> MarketDataProvider:
    provider_type = provider_config.get("type")
    if provider_type == "synthetic":
        return SyntheticMarketDataProvider()
    if provider_type == "yfinance":
        from data.providers.yfinance_provider import YFinanceProvider
        return YFinanceProvider()
    if provider_type == "csv":
        from data.providers.csv_provider import CSVMarketDataProvider
        path = provider_config.get("path")
        if not path:
            raise ValueError(f"Provider '{provider_id}' of type csv requires path")
        return CSVMarketDataProvider(path)
    if provider_type == "broker_api":
        raise NotImplementedError(
            f"Provider '{provider_id}' is configured for a broker API, but no adapter is implemented yet"
        )
    raise ValueError(f"Unknown provider type '{provider_type}' for provider '{provider_id}'")
