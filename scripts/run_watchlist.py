"""Build a daily, config-driven underlying-index research watchlist (no order execution)."""
import argparse
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from backtesting.engine import run_strategy_backtest
from core.base.models import BacktestConfig, validate_ohlcv
from core.configuration.environment import load_environment
from core.configuration.loader import CONFIG_DIR, REPOSITORY_ROOT, load_catalog
from data.registry import create_provider
from strategies.registry import create_strategy


def _load_watchlist(config_dir: Path) -> dict[str, Any]:
    path = config_dir / "research_universe.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Watchlist configuration not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle) or {}
    watchlist = value.get("watchlist")
    if not isinstance(watchlist, dict):
        raise ValueError(f"Expected a 'watchlist' mapping in {path}")
    datasets = watchlist.get("datasets")
    strategies = watchlist.get("strategies")
    if not isinstance(datasets, list) or not datasets:
        raise ValueError("watchlist.datasets must be a non-empty list")
    if not isinstance(strategies, list) or not strategies:
        raise ValueError("watchlist.strategies must be a non-empty list")
    if len(set(datasets)) != len(datasets) or len(set(strategies)) != len(strategies):
        raise ValueError("watchlist dataset and strategy IDs must be unique")
    period = watchlist.get("period", {})
    start = date.fromisoformat(str(period.get("start", "")))
    if start >= date.today():
        raise ValueError("watchlist.period.start must be earlier than today")
    if period.get("end", "previous_day") not in {"previous_day", "latest"}:
        date.fromisoformat(str(period["end"]))
    discovery = watchlist.get("discovery", {})
    if discovery and not isinstance(discovery, dict):
        raise ValueError("watchlist.discovery must be a mapping")
    if discovery.get("enabled", False):
        if not discovery.get("provider"):
            raise ValueError("watchlist.discovery.provider is required when discovery is enabled")
        if not discovery.get("exchanges") or not discovery.get("prefixes"):
            raise ValueError("watchlist.discovery requires non-empty exchanges and prefixes")
    return watchlist


def _period_dates(watchlist: dict[str, Any], start_override: str | None,
                  end_override: str | None) -> tuple[str, str, date]:
    period = watchlist["period"]
    start = start_override or str(period["start"])
    end_config = period.get("end", "previous_day")
    if end_override:
        end = end_override
    elif end_config in {"previous_day", "latest"}:
        # Avoid relying on an in-progress daily candle while the market is open.
        end = (date.today() - timedelta(days=1)).isoformat()
    else:
        end = str(end_config)
    start_date, end_date = date.fromisoformat(start), date.fromisoformat(end)
    if start_date > end_date:
        raise ValueError("Research start date must be on or before end date")
    return start_date.isoformat(), end_date.isoformat(), end_date


def _required_environment(provider_config: dict[str, Any]) -> list[str]:
    provider_type = provider_config.get("type")
    keys: list[str] = []
    if provider_type == "kite_connect":
        keys = [provider_config.get("api_key_env", "KITE_API_KEY"),
                provider_config.get("access_token_env", "KITE_ACCESS_TOKEN")]
    elif provider_type == "groww":
        keys = [provider_config.get("token_env", "GROWW_ACCESS_TOKEN")]
    elif provider_type == "rest_json":
        auth = provider_config.get("auth", {})
        if auth:
            keys = [auth.get("token_env", "")]
    import os

    return [key for key in keys if key and (
        not os.environ.get(key, "").strip()
        or os.environ.get(key, "").strip().lower() in {"replace_me", "your_api_key", "your_token"}
    )]


def _signal_summary(signal_frame: pd.DataFrame) -> dict[str, Any]:
    if "signal" not in signal_frame or signal_frame.empty:
        raise ValueError("Strategy output must include a non-empty signal column")
    signal = pd.to_numeric(signal_frame["signal"], errors="raise")
    if signal.isna().any():
        raise ValueError("Strategy output contains missing signal values")
    current = float(signal.iloc[-1])
    previous = float(signal.iloc[-2]) if len(signal) > 1 else 0.0
    if previous <= 0 and current > 0:
        event = "BULLISH_CROSSOVER"
    elif previous > 0 and current <= 0:
        event = "BEARISH_CROSSOVER"
    elif current > 0:
        event = "BULLISH_STATE"
    else:
        event = "FLAT_STATE"
    output: dict[str, Any] = {
        "signal_state": "LONG" if current > 0 else "FLAT",
        "signal_event": event,
        "signal_value": current,
    }
    for column, name in (("fast_ma", "fast_ma"), ("slow_ma", "slow_ma"),
                         ("rsi", "rsi"), ("macd", "macd"),
                         ("signal_line", "macd_signal_line")):
        if column in signal_frame:
            value = signal_frame[column].iloc[-1]
            output[name] = float(value) if pd.notna(value) else None
    if "fast_ma" in signal_frame and "slow_ma" in signal_frame:
        fast, slow = output.get("fast_ma"), output.get("slow_ma")
        if fast is not None and slow is not None and slow != 0:
            output["ma_spread_pct"] = float((fast / slow - 1.0) * 100.0)
    return output


def _format_pct(value: Any) -> str:
    try:
        return f"{float(value):.2%}"
    except (TypeError, ValueError):
        return "n/a"


def _write_reports(rows: list[dict[str, Any]], output_dir: Path,
                   start: str, end: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    if not frame.empty:
        priority = {
            "BULLISH_CROSSOVER": 0, "BEARISH_CROSSOVER": 1,
            "BULLISH_STATE": 2, "FLAT_STATE": 3,
        }
        frame["_signal_priority"] = frame.get("signal_event", pd.Series(index=frame.index)).map(
            priority
        ).fillna(9)
        frame["_status_priority"] = frame.get("run_status", pd.Series(index=frame.index)).map(
            {"OK": 0, "STALE_DATA": 1, "ERROR": 2}
        ).fillna(9)
        frame = frame.sort_values(
            ["_status_priority", "_signal_priority", "sharpe_ratio"],
            ascending=[True, True, False], na_position="last"
        ).drop(columns=["_signal_priority", "_status_priority"])
    csv_path = output_dir / "watchlist.csv"
    report_path = output_dir / "watchlist.md"
    frame.to_csv(csv_path, index=False)
    lines = [
        "# AlgoTrade Daily Research Watchlist", "",
        f"- Requested data window: {start} through {end}",
        f"- Generated: {pd.Timestamp.now().isoformat(timespec='seconds')}",
        f"- Configured rows: {len(frame)}",
        f"- Successful rows: {int(frame.get('run_status', pd.Series(dtype=str)).isin(['OK', 'STALE_DATA']).sum())}",
        f"- Failed rows: {int((frame.get('run_status', pd.Series(dtype=str)) == 'ERROR').sum())}", "",
        "> Research output only. It does not place orders or recommend a trade. "
        "The daily backtest models close-derived signals filled at the next open, but does not "
        "model bid/ask quotes, liquidity or partial fills. F&O requires a separate contract-level workflow.", "",
        "| Dataset | Strategy | Signal event | Latest bar | Data status | CAGR | Sharpe | Max drawdown |",
        "|---|---|---|---|---|---:|---:|---:|",
    ]
    for row in frame.to_dict(orient="records"):
        lines.append(
            f"| {row.get('dataset_id', '')} | {row.get('strategy_id', '')} "
            f"| {row.get('signal_event', 'n/a')} | {row.get('last_bar_date', 'n/a')} "
            f"| {row.get('run_status', 'ERROR')} | {_format_pct(row.get('cagr'))} "
            f"| {row.get('sharpe_ratio', 'n/a')} | {_format_pct(row.get('max_drawdown'))} |"
        )
    lines.extend(["", "## How to interpret this report", "",
                  "- A crossover is a technical event, not a trade instruction.",
                  "- A stale or failed data row must not be used for a current decision.",
                  "- Strategy results are historical and sensitive to data, costs and execution assumptions.",
                  "- The index watchlist does not automatically select a futures or options contract.",
                  "- Review the CSV for provider, symbol, row counts, date freshness, costs and error details.", "",
                  f"Machine-readable report: {csv_path.as_posix()}", ""])
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return csv_path, report_path



def _resolve_dataset_items(
    catalog: dict[str, Any],
    watchlist: dict[str, Any],
    provider_cache: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    """Resolve either configured datasets or dynamically discovered Kite index instruments."""
    discovery = watchlist.get("discovery", {})
    if not discovery.get("enabled", False):
        return [
            (dataset_id, catalog["datasets"][dataset_id])
            for dataset_id in watchlist["datasets"]
        ]

    provider_id = str(discovery["provider"])
    if provider_id not in catalog["providers"]:
        raise ValueError(f"Index discovery references unknown provider '{provider_id}'")
    provider_config = catalog["providers"][provider_id]
    missing_env = _required_environment(provider_config)
    if missing_env:
        raise RuntimeError(
            "Missing/placeholder credentials for index discovery: " + ", ".join(missing_env)
            + ". Set them in the repository-root .env file."
        )
    if provider_id not in provider_cache:
        provider_cache[provider_id] = create_provider(provider_id, provider_config)
    provider = provider_cache[provider_id]
    discover = getattr(provider, "list_index_instruments", None)
    if not callable(discover):
        raise RuntimeError(
            f"Provider '{provider_id}' does not support automatic index discovery. "
            "Disable discovery and configure watchlist.datasets explicitly."
        )
    found = discover(
        tuple(str(value).upper() for value in discovery["exchanges"]),
        tuple(str(value).upper() for value in discovery["prefixes"]),
    )
    items: list[tuple[str, dict[str, Any]]] = []
    for instrument in found.to_dict(orient="records"):
        exchange = str(instrument["exchange"]).upper()
        trading_symbol = str(instrument["tradingsymbol"])
        token = str(int(instrument["instrument_token"]))
        dataset_id = re.sub(r"[^a-z0-9]+", "_", f"{exchange}_{trading_symbol}".lower()).strip("_")
        items.append((dataset_id, {
            "provider": provider_id,
            "symbol": token,
            "display_symbol": f"{exchange}:{trading_symbol}",
            "exchange": exchange,
            "instrument_name": str(instrument.get("name", trading_symbol)),
            "data_kind": "index",
            "interval": "1d",
        }))
    if not items:
        raise ValueError("Index discovery returned no NIFTY/SENSEX instruments")
    return items

def run_watchlist(config_dir: Path, start_override: str | None = None,
                  end_override: str | None = None) -> tuple[Path, Path]:
    load_environment()
    catalog = load_catalog(config_dir)
    watchlist = _load_watchlist(config_dir)
    start, end, end_date = _period_dates(watchlist, start_override, end_override)
    max_age = int(watchlist.get("max_data_age_calendar_days", 5))
    if max_age < 0:
        raise ValueError("max_data_age_calendar_days must be non-negative")
    for dataset_id in watchlist["datasets"]:
        if dataset_id not in catalog["datasets"]:
            raise ValueError(f"Watchlist references unknown dataset '{dataset_id}'")
    for strategy_id in watchlist["strategies"]:
        if strategy_id not in catalog["strategies"]:
            raise ValueError(f"Watchlist references unknown strategy '{strategy_id}'")

    rows: list[dict[str, Any]] = []
    data_cache: dict[str, pd.DataFrame] = {}
    provider_cache: dict[str, Any] = {}
    try:
        dataset_items = _resolve_dataset_items(catalog, watchlist, provider_cache)
    except Exception as exc:
        discovery = watchlist.get("discovery", {})
        provider_id = str(discovery.get("provider", "unknown"))
        for strategy_id in watchlist["strategies"]:
            rows.append({
                "dataset_id": "index_discovery",
                "symbol": "NIFTY*/SENSEX*",
                "provider_id": provider_id,
                "strategy_id": strategy_id,
                "start_date": start,
                "end_date": end,
                "run_status": "ERROR",
                "signal_state": "UNKNOWN",
                "signal_event": "UNKNOWN",
                "error": f"{type(exc).__name__}: {exc}",
            })
        dataset_items = []
    for dataset_id, dataset in dataset_items:
        provider_id = dataset["provider"]
        provider_config = catalog["providers"][provider_id]
        base: dict[str, Any] = {
            "dataset_id": dataset_id,
            "symbol": dataset.get("display_symbol", dataset["symbol"]),
            "provider_symbol": dataset["symbol"],
            "exchange": dataset.get("exchange", ""),
            "instrument_name": dataset.get("instrument_name", ""),
            "data_kind": dataset.get("data_kind", "ohlcv"),
            "provider_id": provider_id,
            "start_date": start,
            "end_date": end,
        }
        try:
            missing_env = _required_environment(provider_config)
            if missing_env:
                raise RuntimeError(
                    "Missing/placeholder credentials: " + ", ".join(missing_env)
                    + ". Set them in the repository-root .env file."
                )
            if dataset_id not in data_cache:
                if provider_id not in provider_cache:
                    provider_cache[provider_id] = create_provider(provider_id, provider_config)
                market_data = provider_cache[provider_id].get_history(dataset["symbol"], start, end)
                market_data = validate_ohlcv(market_data)
                start_date, requested_end_date = date.fromisoformat(start), date.fromisoformat(end)
                in_range = [
                    start_date <= pd.Timestamp(timestamp).date() <= requested_end_date
                    for timestamp in market_data.index
                ]
                market_data = market_data.loc[in_range]
                if market_data.empty:
                    raise ValueError("No valid candles remain after applying the requested date range")
                data_cache[dataset_id] = market_data
            data = data_cache[dataset_id]
        except Exception as exc:
            for strategy_id in watchlist["strategies"]:
                rows.append({
                    **base,
                    "strategy_id": strategy_id,
                    "run_status": "ERROR",
                    "last_bar_date": "",
                    "data_age_calendar_days": None,
                    "rows": 0,
                    "signal_state": "UNKNOWN",
                    "signal_event": "UNKNOWN",
                    "error": f"{type(exc).__name__}: {exc}",
                })
            continue

        last_bar_date = pd.Timestamp(data.index[-1]).date()
        age_days = (end_date - last_bar_date).days
        data_status = "STALE_DATA" if age_days > max_age else "OK"
        for strategy_id in watchlist["strategies"]:
            try:
                strategy = create_strategy(strategy_id, catalog["strategies"][strategy_id])
                signal_frame = strategy.generate_signals(data)
                signal_info = _signal_summary(signal_frame)
                settings = catalog["defaults"].get("backtest", {})
                _, metrics = run_strategy_backtest(
                    data,
                    strategy,
                    BacktestConfig(
                        initial_capital=float(settings.get("initial_capital", 100_000)),
                        transaction_cost_bps=float(settings.get("transaction_cost_bps", 10)),
                        risk_free_rate=float(settings.get("risk_free_rate", 0)),
                        slippage_bps=float(settings.get("slippage_bps", 0)),
                    ),
                )
                rows.append({
                    **base,
                    **signal_info,
                    "strategy_id": strategy_id,
                    "run_status": data_status,
                    "last_bar_date": last_bar_date.isoformat(),
                    "data_age_calendar_days": age_days,
                    "rows": int(len(data)),
                    "cagr": metrics.get("cagr"),
                    "total_return": metrics.get("total_return"),
                    "sharpe_ratio": metrics.get("sharpe_ratio"),
                    "max_drawdown": metrics.get("max_drawdown"),
                    "annualized_volatility": metrics.get("annualized_volatility"),
                    "entry_count": metrics.get("entry_count"),
                    "exit_count": metrics.get("exit_count"),
                    "transaction_cost_bps": float(settings.get("transaction_cost_bps", 10)),
                    "slippage_bps": float(settings.get("slippage_bps", 0)),
                    "error": "",
                })
            except Exception as exc:
                rows.append({
                    **base,
                    "strategy_id": strategy_id,
                    "run_status": "ERROR",
                    "last_bar_date": last_bar_date.isoformat(),
                    "data_age_calendar_days": age_days,
                    "rows": int(len(data)),
                    "signal_state": "UNKNOWN",
                    "signal_event": "UNKNOWN",
                    "error": f"{type(exc).__name__}: {exc}",
                })

    configured_output = Path(watchlist.get("output_dir", "reports/watchlist"))
    output_dir = configured_output if configured_output.is_absolute() else REPOSITORY_ROOT / configured_output
    return _write_reports(rows, output_dir, start, end)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate or run the configured daily index/equity research watchlist."
    )
    parser.add_argument("--config-dir", default=None, help="Directory containing YAML catalogs")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate configuration and credential readiness")
    validate.add_argument("--start", default=None)
    validate.add_argument("--end", default=None)
    run = commands.add_parser("run", help="Fetch data and write watchlist CSV/Markdown")
    run.add_argument("--start", default=None)
    run.add_argument("--end", default=None)
    args = parser.parse_args()
    config_dir = Path(args.config_dir).expanduser().resolve() if args.config_dir else CONFIG_DIR
    load_environment()
    catalog = load_catalog(config_dir)
    watchlist = _load_watchlist(config_dir)
    start, end, _ = _period_dates(watchlist, args.start, args.end)
    unknown_datasets = sorted(set(watchlist["datasets"]) - set(catalog["datasets"]))
    unknown_strategies = sorted(set(watchlist["strategies"]) - set(catalog["strategies"]))
    if unknown_datasets or unknown_strategies:
        raise ValueError(
            f"Unknown references: datasets={unknown_datasets}, strategies={unknown_strategies}"
        )
    discovery = watchlist.get("discovery", {})
    discovery_enabled = bool(discovery.get("enabled", False))
    print(f"Watchlist config valid. Period: {start} through {end}")
    if discovery_enabled:
        print(
            f"Index discovery enabled: provider={discovery['provider']}, "
            f"exchanges={discovery['exchanges']}, prefixes={discovery['prefixes']}"
        )
    else:
        print(f"Configured datasets: {len(watchlist['datasets'])}")
    print(f"Strategies: {len(watchlist['strategies'])}")
    if args.command == "validate":
        if discovery_enabled:
            provider_id = discovery["provider"]
            provider = catalog["providers"][provider_id]
            missing = _required_environment(provider)
            state = "MISSING CREDENTIALS: " + ", ".join(missing) if missing else "credentials present"
            print(f"- discovery provider {provider_id}: {state}")
        else:
            for dataset_id in watchlist["datasets"]:
                dataset = catalog["datasets"][dataset_id]
                provider = catalog["providers"][dataset["provider"]]
                missing = _required_environment(provider)
                state = "MISSING CREDENTIALS: " + ", ".join(missing) if missing else "credentials present"
                print(f"- {dataset_id} ({dataset['provider']} / {dataset['symbol']}): {state}")
        print("Validation does not make network requests; run the command to test actual provider access.")
        return
    csv_path, report_path = run_watchlist(config_dir, args.start, args.end)
    print(f"CSV: {csv_path}")
    print(f"Markdown report: {report_path}")


if __name__ == "__main__":
    main()
