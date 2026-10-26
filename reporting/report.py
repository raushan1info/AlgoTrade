"""Human-readable backtest report output."""
from pathlib import Path

import pandas as pd


def _format_metric(key: str, value: float) -> str:
    if key in {"total_return", "cagr", "annualized_volatility", "max_drawdown",
               "buy_hold_total_return", "buy_hold_cagr", "buy_hold_max_drawdown",
               "exposure_pct"}:
        return f"{value:.2%}"
    if key in {"trading_days", "entry_count", "exit_count"}:
        return f"{int(value):,}"
    return f"{value:,.2f}"


def write_report(results: pd.DataFrame, metrics: dict[str, float],
                 output_dir: str | Path = "reports") -> tuple[Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / "backtest_results.csv"
    report_path = output / "backtest_report.md"
    results.to_csv(csv_path, index_label="Date")
    labels = {
        "total_return": "Total return", "cagr": "CAGR (annualized)",
        "annualized_volatility": "Annualized volatility", "sharpe_ratio": "Sharpe ratio",
        "max_drawdown": "Maximum drawdown", "trading_days": "Trading days",
        "entry_count": "Entries", "exit_count": "Exits", "exposure_pct": "Exposure",
        "total_turnover": "Cumulative turnover", "initial_capital": "Initial capital",
        "final_equity": "Final equity",
    }
    lines = ["# AlgoTrade Backtest Report", "",
             "> Educational research output, not investment advice.", "", "| Metric | Value |", "|---|---:|"]
    for key, label in labels.items():
        if key in metrics:
            lines.append(f"| {label} | {_format_metric(key, metrics[key])} |")
    lines += ["", f"Detailed daily results: {csv_path.as_posix()}", ""]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path, csv_path


def write_experiment_report(summary: pd.DataFrame, experiment: dict,
                            output_dir: str | Path) -> tuple[Path, Path]:
    """Write combination-level metrics to CSV and a Markdown comparison."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / "experiment_summary.csv"
    report_path = output / "experiment_report.md"
    summary.to_csv(csv_path, index=False)
    lines = [
        f"# Experiment: {experiment.get('description', 'AlgoTrade research run')}", "",
        "> Educational research output, not investment advice.", "",
        f"- Period: {experiment['period']['start']} to {experiment['period']['end']}",
        f"- Dataset count: {len(experiment['datasets'])}",
        f"- Strategy count: {len(experiment['strategies'])}", "",
        "| Dataset | Symbol | Data source | Strategy | Total return | CAGR | Sharpe | Max DD | Buy/hold return | Entries / exits | Trading days |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.to_dict(orient="records"):
        source_label = f"{row.get('provider_id', '')} / {row.get('data_kind', '')}"
        lines.append(
            f"| {row['dataset_id']} | {row['symbol']} | {source_label} | {row['strategy_id']} "
            f"| {row['total_return']:.2%} | {row['cagr']:.2%} | {row['sharpe_ratio']:.3f} "
            f"| {row['max_drawdown']:.2%} | {row['buy_hold_total_return']:.2%} "
            f"| {int(row['entry_count'])} / {int(row['exit_count'])} | {int(row['trading_days'])} |"
        )
    lines += [
        "", "Note: strategy returns include configured turnover-based transaction costs. "
        "The buy-and-hold benchmark is gross of transaction costs.", "",
        f"Full combination metrics: {csv_path.as_posix()}", "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path, csv_path
