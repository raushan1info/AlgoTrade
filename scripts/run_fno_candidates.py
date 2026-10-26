"""Generate dated, research-only F&O candidates from underlying-index signals."""
import argparse
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from core.configuration.environment import load_environment
from core.configuration.loader import CONFIG_DIR, REPOSITORY_ROOT, load_catalog
from core.market_data.contract_selection import select_contracts
from data.registry import create_provider
from strategies.registry import create_strategy


def _load_derivatives_config(config_dir: Path) -> dict[str, Any]:
    path = config_dir / "derivatives.yaml"
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    config = payload.get("derivatives")
    if not isinstance(config, dict) or not isinstance(config.get("underlyings"), list):
        raise ValueError(f"Expected derivatives.underlyings list in {path}")
    if not config["underlyings"]:
        raise ValueError("derivatives.underlyings must not be empty")
    seen: set[str] = set()
    for item in config["underlyings"]:
        for key in ("id", "index_symbol", "derivative_underlying", "exchange", "strategy", "policy"):
            if key not in item:
                raise ValueError(f"Each derivatives underlying requires '{key}'")
        if item["id"] in seen:
            raise ValueError(f"Duplicate derivative underlying id: {item['id']}")
        seen.add(item["id"])
        if item["exchange"] not in {"NSE", "BSE"}:
            raise ValueError(f"Unsupported underlying exchange for {item['id']}: {item['exchange']}")
        if not isinstance(item["policy"], dict):
            raise ValueError(f"Policy for {item['id']} must be a mapping")
    return config


def _provider_ready(provider_config: dict[str, Any]) -> None:
    import os

    provider_type = provider_config.get("type")
    if provider_type == "kite_connect":
        keys = [
            provider_config.get("api_key_env", "KITE_API_KEY"),
            provider_config.get("access_token_env", "KITE_ACCESS_TOKEN"),
        ]
    elif provider_type == "groww":
        keys = [provider_config.get("token_env", "GROWW_ACCESS_TOKEN")]
    else:
        keys = []
    missing = [
        key for key in keys
        if not os.environ.get(key, "").strip()
        or os.environ.get(key, "").strip().lower()
        in {"replace_me", "your_api_key", "your_token"}
    ]
    if missing:
        raise RuntimeError("Missing/placeholder credentials: " + ", ".join(missing))


def run_candidates(config_dir: Path, end_override: str | None = None) -> tuple[Path, Path]:
    load_environment()
    catalog = load_catalog(config_dir)
    config = _load_derivatives_config(config_dir)
    provider_id = str(config.get("provider", ""))
    if provider_id not in catalog["providers"]:
        raise ValueError(f"Unknown derivatives provider: {provider_id}")
    provider_config = catalog["providers"][provider_id]
    _provider_ready(provider_config)
    provider = create_provider(provider_id, provider_config)
    run_date = date.fromisoformat(end_override) if end_override else date.today() - timedelta(days=1)
    start = date.fromisoformat(str(config.get("history_start", "2025-01-01")))
    if start > run_date:
        raise ValueError("derivatives.history_start must be on or before the report date")

    rows: list[dict[str, Any]] = []
    for item in config["underlyings"]:
        base = {
            "underlying_id": item["id"],
            "index_symbol": item["index_symbol"],
            "derivative_underlying": item["derivative_underlying"],
            "provider_id": provider_id,
            "strategy_id": item["strategy"],
            "report_date": run_date.isoformat(),
            "signal_date": None,
            "signal_state": "UNKNOWN",
            "signal_value": None,
            "spot_close": None,
            "candidate_status": "ERROR",
            "error": "",
        }
        try:
            if item["strategy"] not in catalog["strategies"]:
                raise ValueError(f"Unknown strategy '{item['strategy']}'")
            candles = provider.get_history(item["index_symbol"], start.isoformat(), run_date.isoformat())
            candles = candles.loc[
                (pd.to_datetime(candles.index).date >= start)
                & (pd.to_datetime(candles.index).date <= run_date)
            ].sort_index()
            if candles.empty:
                raise ValueError("No underlying candles in requested period")
            signal_date = pd.Timestamp(candles.index[-1]).date()
            age_days = (run_date - signal_date).days
            spot = float(candles["Close"].iloc[-1])
            strategy = create_strategy(item["strategy"], catalog["strategies"][item["strategy"]])
            signal_frame = strategy.generate_signals(candles)
            if "signal" not in signal_frame or signal_frame.empty:
                raise ValueError("Strategy output has no signal column")
            signal_value = float(signal_frame["signal"].iloc[-1])
            if pd.isna(signal_value):
                raise ValueError("Latest strategy signal is missing")
            signal_state = "LONG" if signal_value > 0 else "FLAT"
            base.update({
                "signal_date": signal_date.isoformat(),
                "signal_state": signal_state,
                "signal_value": signal_value,
                "spot_close": spot,
                "data_age_calendar_days": age_days,
            })
            max_age = int(config.get("max_data_age_calendar_days", 5))
            if age_days > max_age:
                base.update({
                    "candidate_status": "STALE_DATA",
                    "error": f"Latest underlying candle is {age_days} calendar days old (limit {max_age})",
                })
                rows.append(base)
                continue
            if signal_state == "FLAT" and not item["policy"].get("allow_flat_signal", False):
                base.update({
                    "candidate_status": "NO_SIGNAL",
                    "selection_reason": "Configured strategy is FLAT; policy does not select a contract",
                    "liquidity_status": "NOT_CHECKED",
                })
                rows.append(base)
                continue

            derivative_exchange = "NFO" if item["exchange"] == "NSE" else "BFO"
            contracts = provider.list_derivative_contracts(
                item["derivative_underlying"], run_date, exchanges=(derivative_exchange,)
            )
            selected = select_contracts(
                contracts,
                underlying=item["derivative_underlying"],
                as_of=run_date,
                spot_price=spot,
                signal_state=signal_state,
                policy=item["policy"],
            )
            if not selected:
                base.update({
                    "candidate_status": "NO_ELIGIBLE_CONTRACT",
                    "error": (
                        "No contract met the configured kind, expiry, signal and moneyness policy. "
                        "Check provider coverage and the current instrument master."
                    ),
                    "liquidity_status": "UNKNOWN_NOT_PROVIDED",
                })
                rows.append(base)
                continue
            for contract in selected:
                rows.append({
                    **base,
                    **contract,
                    "candidate_status": "CANDIDATE_REQUIRES_REVIEW",
                    "error": "",
                    "data_age_calendar_days": age_days,
                    "signal_to_contract_note": (
                        "Candidate is mapped from the underlying signal; it is not a trade instruction. "
                        "Liquidity/OI, bid-ask spread, premium budget, transaction costs and risk are not validated."
                    ),
                })
        except Exception as exc:
            rows.append({**base, "candidate_status": "ERROR", "error": f"{type(exc).__name__}: {exc}"})

    output_dir = Path(str(config.get("output_dir", "reports/fno_candidates")))
    if not output_dir.is_absolute():
        output_dir = REPOSITORY_ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "fno_candidates.csv"
    md_path = output_dir / "fno_candidates.md"
    frame = pd.DataFrame(rows)
    frame.to_csv(csv_path, index=False)
    lines = [
        "# F&O Research Candidate Watchlist", "",
        f"- Report date: {run_date.isoformat()}",
        f"- Provider: {provider_id}",
        f"- Underlyings configured: {len(config['underlyings'])}",
        f"- Candidate rows: {int(frame.get('candidate_status', pd.Series(dtype=str)).eq('CANDIDATE_REQUIRES_REVIEW').sum())}",
        "", "> Research-only output. No orders are placed. Current instrument-master discovery cannot reconstruct expired contracts.",
        "> Liquidity/open interest and bid-ask spread are not provided by this discovery path and remain unknown.",
        "> The configured MA strategy is long/flat; a flat signal does not imply a bearish signal or justify a put.",
        "", "| Underlying | Signal date | State | Spot close | Contract | Expiry | Strike | Type | DTE | Status |",
        "|---|---|---|---:|---|---|---:|---|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('derivative_underlying', '')} | {row.get('signal_date') or 'n/a'} "
            f"| {row.get('signal_state', 'UNKNOWN')} | {row.get('spot_close', 'n/a')} "
            f"| {row.get('instrument_id', 'n/a')} | {row.get('expiry', 'n/a')} "
            f"| {row.get('strike', 'n/a')} | {row.get('option_type') or row.get('kind', 'n/a')} "
            f"| {row.get('days_to_expiry', 'n/a')} | {row.get('candidate_status', 'ERROR')} |"
        )
        if row.get("error"):
            lines.append(f"  - {row.get('derivative_underlying', '')}: {row['error']}")
    lines.extend([
        "", "## Selection and interpretation", "",
        "- Underlying signals are generated from the configured strategy and latest available index candle.",
        "- Options use the nearest eligible expiry within the configured DTE bounds and the closest strike to spot within the moneyness limit.",
        "- Lot size, tick size, expiry and token are read from the provider's current instrument master, not hard-coded.",
        "- Liquidity is explicitly unknown because this provider discovery path does not retrieve point-in-time OI/volume or bid/ask quotes.",
        "- A candidate is not validated for premium affordability, spread, margin, transaction costs, expiry settlement or suitability.",
        "- For historical F&O research, use archived point-in-time instrument masters and exact contract history; today's master is insufficient.",
        "", f"Machine-readable report: {csv_path.as_posix()}", "",
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return csv_path, md_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a research-only F&O candidate list from underlying index signals."
    )
    parser.add_argument("--config-dir", default=None, help="Directory containing YAML catalogs")
    parser.add_argument("--end", default=None, help="Report end date (YYYY-MM-DD); defaults to previous calendar day")
    args = parser.parse_args()
    config_dir = Path(args.config_dir).expanduser().resolve() if args.config_dir else CONFIG_DIR
    csv_path, md_path = run_candidates(config_dir, args.end)
    print(f"CSV: {csv_path}")
    print(f"Markdown report: {md_path}")


if __name__ == "__main__":
    main()
