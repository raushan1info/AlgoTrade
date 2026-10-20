# AlgoTrade

A modular Python framework for Indian equity research and strategy evaluation. The project starts as a local-first modular monolith: no frontend, API, LLM, or live broker execution is required for the current milestones.

## Quick start

Requires Python 3.10 or newer.

    python -m venv .venv
    # Windows PowerShell: .venv\Scripts\Activate.ps1
    # macOS/Linux: source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -e ".[dev]"
    pytest

## Configuration-driven experiments

Research runs are configured in YAML catalogs under config/. Non-developers can select a named experiment without editing Python code.

    python scripts/run_experiment.py list
    python scripts/run_experiment.py validate --experiment compare_strategies
    python scripts/run_experiment.py run --experiment compare_strategies

Examples included:
- compare_strategies: several strategies on one dataset.
- compare_datasets: one strategy across multiple datasets.
- full_matrix: each selected strategy on each selected dataset.

The runner loads each dataset once per experiment, runs all requested dataset/strategy combinations independently, and writes one CSV per combination plus experiment_summary.csv and experiment_report.md under reports/<experiment-id>/.

Configuration files:
- config/defaults.yaml: common backtest defaults.
- config/providers.yaml: provider types and provider-specific settings.
- config/datasets.yaml: dataset IDs, symbols, intervals, and provider references.
- config/strategies.yaml: reusable strategy IDs and parameters.
- config/experiments.yaml: named runs, periods, selections, and output directories.

## Data sources

The default examples use deterministic synthetic data and work offline. Synthetic data only validates software behavior; it must not be used to draw investment conclusions.

For Yahoo Finance daily data:

    pip install -e ".[market-data]"

Then change the relevant dataset provider in config/datasets.yaml to yahoo_finance, or create a separate dataset entry that references it. Yahoo Finance is an optional convenience source, not a guaranteed production-grade feed. Verify data quality, availability and applicable terms before relying on or redistributing it.

A CSV provider is included. Configure a CSV provider path in config/providers.yaml and reference it from a dataset. The CSV needs a Date/Datetime/Timestamp column plus Open, High, Low and Close; Volume is also required.

A broker API provider is only a placeholder. A real broker adapter requires provider-specific authentication, instrument mapping, rate-limit handling, historical-data support, and compliance with the provider's terms. Never commit API credentials.

## Adding a strategy

Implement strategies/base.py's generate_signals(data) contract in a new strategy module. Return a DataFrame containing a numeric signal column between 0 and 1. Register the type in strategies/registry.py, then create one or more reusable configurations in config/strategies.yaml. Strategies generate signals only; they do not fetch data or place orders.

## Repository boundaries

- core/: shared models, validation and provider contracts
- data/providers/: market data implementations
- data/registry.py: provider factory
- strategies/: strategy implementations and registry
- backtesting/: simulation and experiment orchestration
- analytics/: performance metrics
- reporting/: Markdown and CSV outputs
- config/: provider, dataset, strategy and experiment catalogs
- scripts/: runnable commands
- tests/: automated checks

## Important limitations

This is an educational research prototype, not investment advice or a production trading system. The current backtester is long-only and uses next-bar signal application, fractional exposure, and transaction costs in basis points. It does not fully model slippage, taxes, exchange charges, liquidity, corporate actions, survivorship bias, or broker execution. Validate assumptions and data quality before relying on results.
