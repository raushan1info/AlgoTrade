# Configuration-driven experiments

AlgoTrade uses YAML catalogs to separate data access, strategy parameters, and experiment intent.

## Run commands

Install dependencies and the project in editable mode:

    pip install -e ".[dev]"
    python scripts/run_experiment.py list
    python scripts/run_experiment.py validate --experiment full_matrix
    python scripts/run_experiment.py run --experiment compare_strategies

Use --config-dir to point at a different directory containing the five YAML catalog files.

## Configuration responsibilities

- defaults.yaml: common backtest defaults.
- providers.yaml: provider implementations and provider-specific configuration.
- datasets.yaml: instrument, timeframe, and provider reference.
- strategies.yaml: strategy type and its parameters.
- experiments.yaml: named combinations, date period, output location, and optional backtest overrides.

An experiment with N datasets and M strategies executes N x M independent backtests. Dataset data is loaded once per dataset within that experiment and reused for its strategies. Results are saved per dataset/strategy pair, plus a summary CSV and Markdown report.

## Add a provider

Implement MarketDataProvider.get_history(symbol, start, end), normalize output to Date-indexed Open, High, Low, Close, Volume columns, then register the provider type in data/registry.py and configure it in providers.yaml. Never commit credentials. Read secrets from environment variables in a future authenticated adapter.

The generic `rest_json` provider supports a single HTTP GET endpoint returning a JSON list of candle objects. Configure `url`, `query_params`, `headers`, `response_path`, and `field_map` in `providers.yaml`. Query templates can use `{symbol}`, `{start}`, and `{end}`; header values can use `env:VARIABLE_NAME` (including within strings such as `Bearer env:API_TOKEN`). The adapter does not support pagination or provider-specific login/token refresh flows; implement a dedicated adapter for those cases.

The `broker_api` provider type remains a placeholder and raises a clear error until a concrete broker adapter exists. An exchange name by itself is not an API integration. The included API URL is an example and must be replaced with a real endpoint and matching response mapping.

## Add a strategy

Implement BaseStrategy.generate_signals(data) in a new module. Return a DataFrame containing a numeric signal column between 0 and 1. Register its type in strategies/registry.py, then define reusable parameter sets in strategies.yaml.

Strategies generate signals only. They do not fetch market data, calculate account balances, or place orders.

## Data and research caveats

The synthetic provider is for software tests, not investment conclusions. Yahoo Finance is an optional convenience source; check its data quality and applicable terms. A CSV source requires a Date/Datetime/Timestamp column and OHLCV columns. Corporate actions, survivorship bias, slippage, taxes, exchange charges, liquidity, and live execution are not fully modeled.
