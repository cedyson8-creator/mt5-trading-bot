import signal
import sys
from logger import setup_logger
from mt5_connector import MT5Connector
from trade_manager import TradeManager
from scheduler import Scheduler


def signal_handler(sig, frame):
    log.info("Received shutdown signal, stopping...")
    scheduler.stop()
    connector.disconnect()
    sys.exit(0)


if __name__ == "__main__":
    log = setup_logger()

    log.info("=" * 50)
    log.info("MT5 Multi-Pair Trading Bot Starting")
    log.info("=" * 50)

    connector = MT5Connector()
    if not connector.connect():
        log.error("Failed to connect to MT5. Exiting.")
        sys.exit(1)

    account = connector.get_account_summary()
    if account:
        trade_manager = TradeManager(connector)
        trade_manager.set_daily_balance(account["balance"])

        scheduler = Scheduler(connector, trade_manager)

        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, signal_handler)

        scheduler.start()

        log.info("Bot is running. Press Ctrl+C to stop.")
        try:
            signal.pause() if hasattr(signal, "pause") else None
        except AttributeError:
            import time
            while True:
                time.sleep(1)
    else:
        log.error("Could not retrieve account info")
        connector.disconnect()
