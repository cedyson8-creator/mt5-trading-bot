import argparse
import sys
import config

from config import validate_trading_config, HISTORY_BACKFILL_DAYS
from runtime_options import resolve_runtime_options, format_symbol_listing
from startup_checks import validate_selected_symbols, run_startup_checks, log_issues
from logger import setup_logger
from mt5_connector import MT5Connector
from ml_model import MLTradingModel
from trade_manager import TradeManager


def main():
    parser = argparse.ArgumentParser(description="MT5 trading bot preflight")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", action="store_true", help="Validate dry-run mode")
    mode_group.add_argument("--live", action="store_true", help="Validate live trading mode")
    parser.add_argument("--strict-symbols", action="store_true", help="Fail preflight if any selected symbol is invalid or unavailable")
    parser.add_argument("--list-symbols", action="store_true", help="Print the resolved symbol basket and exit without connecting to MT5")
    parser.add_argument("--pair", action="append", dest="pair_list", help="Validate only this symbol; repeat for multiple pairs")
    parser.add_argument("--pairs", dest="pairs_csv", help="Comma-separated list of symbols to validate")
    parser.add_argument("--pairs-file", dest="pairs_file", help="Text file containing one symbol per line or comma-separated symbols")
    args = parser.parse_args()
    runtime_dry_run, runtime_pairs, pair_sources = resolve_runtime_options(args)

    log = setup_logger()
    if args.list_symbols:
        print(format_symbol_listing(runtime_pairs, pair_sources))
        return 0

    log.info("MT5 bot preflight check")
    log.info(f"Trading pairs: {', '.join(runtime_pairs)}")
    log.info("=" * 50)

    ok, msg = validate_trading_config(dry_run=runtime_dry_run)
    if not ok:
        log.error(msg)
        return 1

    connector = MT5Connector()
    if not connector.connect():
        log.error("Unable to connect to MT5")
        return 1

    valid_pairs, warnings, fatal_issues = validate_selected_symbols(connector, runtime_pairs, strict_symbols=args.strict_symbols)
    log_issues(log, "Symbol validation warnings:", warnings, level="warning")
    if fatal_issues:
        log_issues(log, "Symbol validation failed:", fatal_issues, level="error")
        connector.disconnect()
        return 1

    issues = run_startup_checks(connector, valid_pairs, strict_symbols=args.strict_symbols)
    if issues:
        log_issues(log, "Startup check failed:", issues, level="error")
        connector.disconnect()
        return 1

    account = connector.get_account_summary()
    log.info(f"Connected account balance: {account['balance']:.2f}" if account else "No account summary available")

    if runtime_dry_run:
        log.info("Mode: DRY_RUN")
    else:
        log.info("Mode: LIVE")

    tm = TradeManager(connector, MLTradingModel())
    tm.bootstrap_trade_state(HISTORY_BACKFILL_DAYS)
    tm.reconcile_open_trades()
    tm.write_open_trades_snapshot()

    connector.disconnect()
    log.info("Preflight passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
