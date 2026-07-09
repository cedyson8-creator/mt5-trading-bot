import signal
import sys
import MetaTrader5 as mt5
from logger import setup_logger
from mt5_connector import MT5Connector
from trade_manager import TradeManager
from scheduler import Scheduler
from ml_model import MLTradingModel
from strategy_engine import set_ml_model
from config import STRATEGY, PAIRS, TIMEFRAME, ML_TRAINING_BARS
from api_server import start_api_server


BANNER = """
███╗   ███╗████████╗███████╗    ██████╗  ██████╗ ████████╗
████╗ ████║╚══██╔══╝██╔════╝    ██╔══██╗██╔═══██╗╚══██╔══╝
██╔████╔██║   ██║   █████╗      ██████╔╝██║   ██║   ██║
██║╚██╔╝██║   ██║   ██╔══╝      ██╔══██╗██║   ██║   ██║
██║ ╚═╝ ██║   ██║   ███████╗    ██████╔╝╚██████╔╝   ██║
╚═╝     ╚═╝   ╚═╝   ╚══════╝    ╚═════╝  ╚═════╝    ╚═╝
"""


def signal_handler(sig, frame):
    log.info("Received shutdown signal, stopping...")
    scheduler.stop()
    connector.disconnect()
    sys.exit(0)


def setup_ml(connector):
    model = MLTradingModel()
    if model.load():
        log.info(f"ML model loaded from disk (accuracy: {model.training_accuracy:.2%})")
    else:
        log.info("No saved ML model found. Training on historical data...")
        all_rates = []
        for pair in PAIRS:
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
    log = setup_logger()

    print(BANNER)
    log.info("MT5 Multi-Pair Trading Bot — ML Enhanced")
    log.info("=" * 50)

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
        ml_model = setup_ml(connector) if STRATEGY == "ml" else None

        trade_manager = TradeManager(connector, ml_model)
        trade_manager.set_daily_balance(account["balance"])

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
        while True:
            time.sleep(1)
    else:
        log.error("Could not retrieve account info")
        connector.disconnect()
