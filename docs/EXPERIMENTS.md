# Configuration-driven experiments

AlgoTrade uses YAML catalogs to separate data access, strategy parameters, and experiment intent. The `config/` directory contains YAML only; loaders and validation live in `core/configuration/`.

## Run commands

    pip install -e ".[dev]"
    python scripts/run_experiment.py list
    python scripts/run_experiment.py validate --experiment full_matrix
    python scripts/run_experiment.py run --experiment compare_strategies

Use `--config-dir` to point to another directory containing the five required YAML catalogs. `instruments.yaml` is optional for equity-only workflows.

## Configuration responsibilities

- `defaults.yaml`: shared backtest defaults.
- `providers.yaml`: provider implementations and provider-specific configuration.
- `datasets.yaml`: dataset IDs, symbol, timeframe, and provider reference.
- `strategies.yaml`: strategy type and its parameters.
- `experiments.yaml`: named combinations, period, output location, and optional overrides.
- `instruments.yaml`: index underlyings reserved for derivatives expansion.

An experiment with N datasets and M strategies executes N × M independent backtests. Dataset data is loaded once per dataset within the experiment and reused for its strategies. Results are saved per dataset/strategy pair, plus a summary CSV and Markdown report. The report distinguishes synthetic data from other provider types and includes a gross buy-and-hold benchmark, trade entry/exit counts, exposure, and turnover.

## Validation and readiness

The `validate` command checks catalog structure, references, strategy parameters, date periods, backtest settings, and local readiness. It warns about synthetic datasets, placeholder REST endpoints, missing auth environment variables, missing local CSV files, and the broker placeholder. It does not make network requests or certify a provider's uptime, license, or data quality.

## Add a provider

Implement `MarketDataProvider.get_history(symbol, start, end)`, normalize output to a date-indexed OHLCV DataFrame, register the provider type in `data/registry.py`, and configure it in `providers.yaml`. Provider end dates are inclusive in the application contract. The generic REST provider supports a single GET and does not support pagination or provider-specific token refresh.

## Add a strategy

Implement `BaseStrategy.generate_signals(data)` in a new module. Return a DataFrame containing a numeric `signal` column between 0 and 1. Register its type in `strategies/registry.py`, then define reusable parameters in `strategies.yaml`. Strategies generate signals only; they do not fetch data, calculate account balances, or place orders.

## Data and research caveats

Synthetic data validates software behavior but cannot support investment conclusions. Yahoo Finance is an optional convenience source; check data quality and terms. The current equity backtester is long-only and does not fully model slippage, taxes, exchange charges, liquidity, corporate actions, survivorship bias, or live execution. F&O support is architectural groundwork only; see `FNO_ARCHITECTURE.md`.
