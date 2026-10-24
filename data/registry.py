"""Factory for configured market-data providers."""
from typing import Any

from core.configuration.environment import load_environment
from core.market_data.base import MarketDataProvider
from data.providers.synthetic import SyntheticMarketDataProvider


def create_provider(provider_id: str, provider_config: dict[str, Any]) -> MarketDataProvider:
    load_environment()
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
    if provider_type == "rest_json":
        from data.providers.rest_json_provider import RestJSONMarketDataProvider
        return RestJSONMarketDataProvider(provider_config)
    if provider_type == "kite_connect":
        from data.providers.kite_provider import KiteConnectMarketDataProvider
        return KiteConnectMarketDataProvider(provider_config)
    if provider_type == "groww":
        from data.providers.groww_provider import GrowwMarketDataProvider
        return GrowwMarketDataProvider(provider_config)
    if provider_type == "broker_api":
        raise NotImplementedError(
            f"Provider '{provider_id}' is configured for a broker API, but no adapter is implemented yet"
        )
    raise ValueError(f"Unknown provider type '{provider_type}' for provider '{provider_id}'")
