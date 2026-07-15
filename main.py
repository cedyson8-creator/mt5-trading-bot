import argparse
import signal
import sys
import MetaTrader5 as mt5
import config
from runtime_options import resolve_runtime_options, format_symbol_listing
from logger import setup_logger
from mt5_connector import MT5Connector
from trade_manager import TradeManager
from scheduler import Scheduler
from ml_model import MLTradingModel
from strategy_engine import set_ml_model
from config import STRATEGY, TIMEFRAME, ML_TRAINING_BARS, validate_trading_config, HISTORY_BACKFILL_DAYS
from api_server import start_api_server
from startup_checks import validate_selected_symbols, run_startup_checks, log_issues


BANNER = """
███╗   ███╗████████╗███████╗    ██████╗  ██████╗ ████████╗
████╗ ████║╚══██╔══╝██╔════╝    ██╔══██╗██╔═══██╗╚══██╔══╝
██╔████╔██║   ██║   █████╗      ██████╔╝██║   ██║   ██║
██║╚██╔╝██║   ██║   ██╔══╝      ██╔══██╗██║   ██║   ██║
██║ ╚═╝ ██║   ██║   ███████╗    ██████╔╝╚██████╔╝   ██║
╚═╝     ╚═╝   ╚═╝   ╚══════╝    ╚═════╝  ╚═════╝    ╚═╝
"""

log = None
connector = None
scheduler = None
trade_manager = None


def signal_handler(sig, frame):
    log.info("Received shutdown signal, stopping...")
    try:
        if trade_manager:
            trade_manager.write_open_trades_snapshot()
    except Exception as e:
        log.warning(f"Failed to write shutdown snapshot: {e}")
    if scheduler:
        scheduler.stop()
    if connector:
        connector.disconnect()
    sys.exit(0)


def setup_ml(connector, pairs):
    model = MLTradingModel()
    if model.load():
        log.info(f"ML model loaded from disk (accuracy: {model.training_accuracy:.2%})")
    else:
        log.info("No saved ML model found. Training on historical data...")
        all_rates = []
        for pair in pairs:
            rates = connector.get_rates(pair, TIMEFRAME, bars=ML_TRAINING_BARS)
            if rates is not None and len(rates) > 500:
                all_rates.extend(rates)
                log.info(f"  {pair}: {len(rates)} bars loaded")
        if len(all_rates) > 500:
            model.train_with_feedback(all_rates)
            if model.trained:
                log.info("ML model trained successfully")
            else:
                log.warning("ML model training failed — falling back to hold")
        else:
            log.warning("Not enough data to train ML model")
    set_ml_model(model)
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MT5 trading bot")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", action="store_true", help="Run without sending live orders")
    mode_group.add_argument("--live", action="store_true", help="Enable live trading mode")
    parser.add_argument("--strict-symbols", action="store_true", help="Fail startup if any selected symbol is invalid or unavailable")
    parser.add_argument("--list-symbols", action="store_true", help="Print the resolved symbol basket and exit without connecting to MT5")
    parser.add_argument("--pair", action="append", dest="pair_list", help="Trade only this symbol; repeat for multiple pairs")
    parser.add_argument("--pairs", dest="pairs_csv", help="Comma-separated list of symbols to trade")
    parser.add_argument("--pairs-file", dest="pairs_file", help="Text file containing one symbol per line or comma-separated symbols")
    args = parser.parse_args()
    runtime_dry_run, runtime_pairs, pair_sources = resolve_runtime_options(args)

    log = setup_logger()

    if args.list_symbols:
        print(format_symbol_listing(runtime_pairs, pair_sources))
        sys.exit(0)

    print(BANNER)
    mode = "DRY RUN" if runtime_dry_run else "LIVE TRADING"
    log.info(f"MT5 Multi-Pair Trading Bot — ML Enhanced [{mode}]")
    log.info(f"Trading pairs: {', '.join(runtime_pairs)}")
    log.info("=" * 50)

    ok, msg = validate_trading_config(dry_run=runtime_dry_run)
    if not ok:
        log.error(msg)
        sys.exit(1)
    if not runtime_dry_run:
        log.warning("Live trading enabled. Orders will be sent to the account configured in MT5_LOGIN / MT5_PASSWORD / MT5_SERVER.")

    connector = MT5Connector()
    if not connector.connect():
        log.error("Failed to connect to MT5. Exiting.")
        sys.exit(1)

    terminal = mt5.terminal_info()
    if terminal and not terminal.trade_allowed:
        log.warning("=" * 60)
        log.warning("ALGO TRADING IS DISABLED! Open MT5 -> Ctrl+O -> Expert Advisors")
        log.warning("Check 'Allow Automated Trading' AND click the 'Algo Trading' button")
        log.warning("at the top toolbar until it turns GREEN. Then restart the bot.")
        log.warning("=" * 60)

    account = connector.get_account_summary()
    if account:
        valid_pairs, warnings, fatal_issues = validate_selected_symbols(connector, runtime_pairs, strict_symbols=args.strict_symbols)
        log_issues(log, "Symbol validation warnings:", warnings, level="warning")
        if fatal_issues:
            log_issues(log, "Symbol validation failed:", fatal_issues, level="error")
            connector.disconnect()
            sys.exit(1)

        runtime_pairs = valid_pairs
        config.PAIRS = runtime_pairs
        log.info(f"Validated trading pairs: {', '.join(runtime_pairs)}")

        ml_model = setup_ml(connector, runtime_pairs) if STRATEGY == "ml" else None

        trade_manager = TradeManager(connector, ml_model)
        trade_manager.set_daily_balance(account["balance"])
        trade_manager.bootstrap_trade_state(HISTORY_BACKFILL_DAYS)

        startup_issues = run_startup_checks(connector, runtime_pairs, strict_symbols=args.strict_symbols)
        if startup_issues:
            log_issues(log, "Startup checklist failed:", startup_issues, level="error")
            connector.disconnect()
            sys.exit(1)

        scheduler = Scheduler(connector, trade_manager, ml_model)

        bot_ref = {"connector": connector, "trade_manager": trade_manager, "ml_model": ml_model}
        try:
            start_api_server(bot_ref, port=8080)
        except Exception as e:
            log.warning(f"API server not started: {e}")

        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, signal_handler)

        scheduler.start()

        log.info("Bot is running. Press Ctrl+C to stop.")
        import time
        try:
            while True:
                time.sleep(1)
        finally:
            try:
                trade_manager.write_open_trades_snapshot()
            except Exception as e:
                log.warning(f"Failed to write final snapshot: {e}")
    else:
        log.error("Could not retrieve account info")
        connector.disconnect()
