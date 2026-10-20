"""Human-readable backtest report output."""
from pathlib import Path
import pandas as pd


def write_report(results: pd.DataFrame, metrics: dict[str, float], output_dir: str | Path = "reports") -> tuple[Path, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / "backtest_results.csv"
    report_path = output / "backtest_report.md"
    results.to_csv(csv_path, index_label="Date")
    labels = {"total_return": "Total return", "cagr": "CAGR (annualized)",
              "annualized_volatility": "Annualized volatility", "sharpe_ratio": "Sharpe ratio",
              "max_drawdown": "Maximum drawdown", "trading_days": "Trading days",
              "initial_capital": "Initial capital", "final_equity": "Final equity"}
    lines = ["# AlgoTrade Backtest Report", "", "> Educational research output, not investment advice.", "", "| Metric | Value |", "|---|---:|"]
    for key, label in labels.items():
        value = metrics.get(key)
        if value is None:
            continue
        formatted = f"{value:.2%}" if key in {"total_return", "cagr", "annualized_volatility", "max_drawdown"} else f"{value:,.2f}"
        lines.append(f"| {label} | {formatted} |")
    lines += ["", f"Detailed daily results: {csv_path.as_posix()}", ""]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path, csv_path
