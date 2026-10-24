"""Run an offline demo backtest, or use Yahoo Finance with --provider yfinance."""
import argparse

from config.environment import load_environment
from backtesting.engine import run_momentum_backtest
from core.base.models import BacktestConfig
from data.providers.synthetic import SyntheticMarketDataProvider
from reporting.report import write_report


def main() -> None:
    load_environment()
    parser = argparse.ArgumentParser(description="Run the AlgoTrade momentum backtest.")
    parser.add_argument("--symbol", default="DEMO.NS")
    parser.add_argument("--start", default="2020-01-01")
    parser.add_argument("--end", default="2025-12-31")
    parser.add_argument("--provider", choices=("synthetic", "yfinance"), default="synthetic")
    parser.add_argument("--fast-window", type=int, default=20)
    parser.add_argument("--slow-window", type=int, default=50)
    parser.add_argument("--capital", type=float, default=100_000.0)
    parser.add_argument("--cost-bps", type=float, default=10.0)
    parser.add_argument("--output-dir", default="reports")
    args = parser.parse_args()
    provider = SyntheticMarketDataProvider()
    if args.provider == "yfinance":
        from data.providers.yfinance_provider import YFinanceProvider
        provider = YFinanceProvider()
    market_data = provider.get_history(args.symbol, args.start, args.end)
    results, metrics = run_momentum_backtest(
        market_data, args.fast_window, args.slow_window,
        BacktestConfig(args.capital, args.cost_bps)
    )
    report_path, csv_path = write_report(results, metrics, args.output_dir)
    print(f"Symbol: {args.symbol} | Provider: {args.provider}")
    for key, value in metrics.items():
        print(f"{key}: {value:.4f}")
    print(f"Report: {report_path}")
    print(f"Daily results: {csv_path}")


if __name__ == "__main__":
    main()
