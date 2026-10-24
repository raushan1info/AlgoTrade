"""Execute named research experiments across dataset/strategy combinations."""
from itertools import product
from pathlib import Path
from typing import Any

import pandas as pd

from analytics.metrics import calculate_metrics
from backtesting.engine import run_strategy_backtest
from core.configuration.loader import resolve_experiment
from core.base.models import BacktestConfig
from data.registry import create_provider
from reporting.report import write_experiment_report
from strategies.registry import create_strategy


def _buy_and_hold_metrics(data: pd.DataFrame, config: BacktestConfig) -> dict[str, float]:
    """Calculate a gross buy-and-hold benchmark on the same price series and date range."""
    close = data["Close"].astype(float)
    returns = close.pct_change().fillna(0.0)
    equity = config.initial_capital * close / close.iloc[0]
    return calculate_metrics(returns, equity, config.risk_free_rate)


def run_experiment(catalog: dict[str, Any], experiment_id: str) -> dict[str, Any]:
    experiment = resolve_experiment(catalog, experiment_id)
    period = experiment["period"]
    settings = experiment["backtest"]
    backtest_config = BacktestConfig(
        initial_capital=float(settings.get("initial_capital", 100_000)),
        transaction_cost_bps=float(settings.get("transaction_cost_bps", 10)),
        risk_free_rate=float(settings.get("risk_free_rate", 0)),
        slippage_bps=float(settings.get("slippage_bps", 0)),
    )
    output_dir = Path(experiment["output_dir"]) / experiment_id
    output_dir.mkdir(parents=True, exist_ok=True)
    summary: list[dict[str, Any]] = []
    cache: dict[str, pd.DataFrame] = {}
    for dataset_id, strategy_id in product(experiment["datasets"], experiment["strategies"]):
        dataset = catalog["datasets"][dataset_id]
        provider_id = dataset["provider"]
        if dataset_id not in cache:
            provider = create_provider(provider_id, catalog["providers"][provider_id])
            cache[dataset_id] = provider.get_history(
                dataset["symbol"], period["start"], period["end"]
            )
        data = cache[dataset_id]
        strategy = create_strategy(strategy_id, catalog["strategies"][strategy_id])
        results, metrics = run_strategy_backtest(data, strategy, backtest_config)
        benchmark = _buy_and_hold_metrics(data, backtest_config)
        pair_id = f"{dataset_id}__{strategy_id}"
        csv_path = output_dir / f"{pair_id}.csv"
        results.to_csv(csv_path, index_label="Date")
        summary.append({
            "experiment_id": experiment_id,
            "dataset_id": dataset_id,
            "symbol": dataset["symbol"],
            "data_kind": dataset.get(
                "data_kind",
                "synthetic" if catalog["providers"][provider_id]["type"] == "synthetic" else "ohlcv",
            ),
            "provider_id": provider_id,
            "strategy_id": strategy_id,
            "strategy_type": catalog["strategies"][strategy_id]["type"],
            **metrics,
            "buy_hold_total_return": benchmark["total_return"],
            "buy_hold_cagr": benchmark["cagr"],
            "buy_hold_sharpe_ratio": benchmark["sharpe_ratio"],
            "buy_hold_max_drawdown": benchmark["max_drawdown"],
            "results_csv": str(csv_path),
        })
        print(
            f"[{dataset_id} x {strategy_id}] CAGR={metrics['cagr']:.2%} "
            f"Sharpe={metrics['sharpe_ratio']:.3f} MaxDD={metrics['max_drawdown']:.2%}"
        )
    summary_frame = pd.DataFrame(summary)
    report_path, summary_path = write_experiment_report(summary_frame, experiment, output_dir)
    return {"summary": summary_frame, "report_path": report_path, "summary_path": summary_path}
