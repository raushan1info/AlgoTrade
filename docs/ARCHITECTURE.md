# Architecture

AlgoTrade is a local-first modular monolith with explicit boundaries and no service/API layer.

- `core/base`: shared backtest and instrument/derivative contract models.
- `core/configuration`: YAML loading, reference validation, provider readiness warnings, and environment setup.
- `core/market_data`: base market-data contract and derivative data interfaces.
- `data/providers`: synthetic, CSV, Yahoo Finance, and generic REST OHLCV providers.
- `data/registry.py`: provider factory.
- `strategies`: pure signal-generation logic; strategies do not fetch data or place orders.
- `backtesting`: long-only equity simulation and experiment orchestration.
- `analytics`: return and risk metrics.
- `reporting`: CSV and Markdown output.
- `scripts`: command-line entry points.
- `tests`: unit and integration checks.

## Configuration

The `config/` directory is declarative YAML only. Python configuration code is in `core/configuration/`. YAML is the single source of truth for providers, datasets, strategies, experiments, defaults, and the underlying index catalog. Default paths resolve from the repository root rather than the caller's current directory.

## Equity data flow

Provider -> OHLCV validation -> Strategy signals -> Backtest engine -> Metrics and buy/hold comparison -> CSV/Markdown report

## Derivatives boundary

Instrument and derivative-contract models plus interfaces are provided, but no F&O provider, point-in-time instrument-master ingestion, options-chain store, lot-based F&O backtest engine, margin model, or broker execution adapter is implemented. See [F&O architecture](FNO_ARCHITECTURE.md).

Future API, UI, LLM, database, and broker integrations should call stable Python interfaces rather than embedding business logic in interface layers.
