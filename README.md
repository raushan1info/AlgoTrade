# AlgoTrade

A local-first modular Python framework for Indian equity research and strategy evaluation. The current application is a modular monolith: no frontend, API, LLM, or live broker execution is required.

## Quick start

Requires Python 3.10 or newer.

    python -m venv .venv
    # Windows PowerShell: .venv\Scripts\Activate.ps1
    # macOS/Linux: source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -e ".[dev]"
    pytest

## Tests and code quality

- `tests/unit/`: isolated module tests.
- `tests/integration/`: connected components and experiment workflows.
- Name test modules `test_<source_module>.py`; keep them inside the unit or integration folder.

    pytest
    pytest tests/unit
    pytest tests/integration
    ruff check .

GitHub Actions checks Python 3.10, 3.11, and 3.12, runs Ruff, and runs pytest.

## Secrets and environment variables

Copy `.env.example` to `.env` in the repository root and replace placeholders with your provider credentials.

    # Windows PowerShell
    Copy-Item .env.example .env
    # macOS/Linux
    cp .env.example .env

The root `.env` file is ignored by Git. Existing process environment variables take precedence. Commit only placeholders in `.env.example`; rotate any credential that has ever been committed. Use GitHub Actions Secrets or a suitable secrets manager outside local development.

## Configuration-driven experiments

The `config/` directory contains declarative YAML only:

- `defaults.yaml`: common backtest defaults.
- `providers.yaml`: provider types and provider-specific settings.
- `datasets.yaml`: dataset IDs, symbols, intervals, and provider references.
- `strategies.yaml`: strategy types and reusable parameters.
- `experiments.yaml`: named runs, date ranges, and dataset/strategy selections.
- `instruments.yaml`: underlying index universe for future derivatives support.

Python loading, validation, and environment setup live under `core/configuration/`.

    python scripts/run_experiment.py list
    python scripts/run_experiment.py validate --experiment compare_strategies
    python scripts/run_experiment.py run --experiment compare_strategies

Examples include comparing multiple strategies on one dataset, one strategy across datasets, and a dataset/strategy matrix. Each run writes per-combination daily CSVs, an experiment summary CSV, and a Markdown report under `reports/<experiment-id>/`.

The validation command checks catalog references and reports local readiness warnings, including synthetic datasets, missing CSVs, missing credentials, placeholder endpoints, and the unimplemented broker provider. It does not make network requests or guarantee provider availability.

## Data sources

The included synthetic provider is deterministic and useful for testing code paths only. Dataset names ending in `_demo` use synthetic data by default; these are **not real historical prices**, even when the symbol field says `RELIANCE.NS`, `TCS.NS`, or another listed instrument.

For Yahoo Finance daily data:

    pip install -e ".[market-data]"

Create a separate dataset using the `yahoo_finance` provider in `config/datasets.yaml`. The adapter requests an inclusive end date from the application's perspective. Yahoo Finance is a convenience source, not a guaranteed production-grade feed; verify availability, data quality, licensing, and redistribution terms.

A CSV provider requires a Date/Datetime/Timestamp column and Open, High, Low, Close, and Volume columns. Relative CSV paths resolve from the repository root. The generic `rest_json` provider supports one GET returning a JSON list of OHLCV records; it does not support pagination or provider-specific token refresh. Its example endpoint is a placeholder and must be replaced.

## Backtest and reporting behavior

The current equity backtester is long-only, uses next-bar signal application, fractional exposure, and configurable turnover-based costs in basis points. Reports include entry/exit counts, exposure, cumulative turnover, and a gross buy-and-hold benchmark for the same price period. Strategy returns include configured transaction costs; the benchmark is currently gross of costs.

The backtester does not fully model slippage, taxes, exchange charges, liquidity, corporate actions, survivorship bias, or broker execution. A daily equity backtest is not an options/futures backtest.

## Futures and Options (F&O)

The repository contains foundational instrument/contract models, derivative market-data interfaces, and an underlying index catalog for NSE NIFTY 50, BANK NIFTY, FINNIFTY, and BSE SENSEX. These do **not** yet provide live or historical F&O data or a lot-based F&O simulation engine.

Read [F&O architecture and roadmap](docs/FNO_ARCHITECTURE.md) before using this as a derivatives framework. A complete implementation requires a dated contract master, historical futures and options-chain data, point-in-time contract selection, lot-based P&L and margin, expiry/settlement handling, and date-versioned Indian-market transaction costs. Do not hard-code lot sizes, expiry schedules, or strike intervals.

## Repository boundaries

- `core/base/`: shared models and OHLCV validation.
- `core/configuration/`: YAML loading, validation, and environment setup.
- `core/market_data/`: provider interfaces.
- `data/providers/`: synthetic, CSV, Yahoo Finance, and generic REST implementations.
- `strategies/`: pure signal-generation modules and registry.
- `backtesting/`: simulation and experiment orchestration.
- `analytics/` and `reporting/`: metrics and CSV/Markdown outputs.
- `scripts/`: command-line entry points.
- `tests/unit/` and `tests/integration/`: automated checks.

This is an educational research prototype, not investment advice or a production trading system.
