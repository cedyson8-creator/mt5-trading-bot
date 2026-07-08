import logging
import csv
import os
from datetime import datetime
from config import LOG_FILE, TRADE_JOURNAL

_logger = None

def setup_logger():
    global _logger
    if _logger:
        return _logger

    _logger = logging.getLogger("MT5Bot")
    _logger.setLevel(logging.INFO)

    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    _logger.addHandler(fh)
    _logger.addHandler(ch)

    return _logger


def get_logger():
    global _logger
    if _logger is None:
        setup_logger()
    return _logger


def log_trade(action, pair, lots, price, sl, tp, reason=""):
    journal_exists = os.path.isfile(TRADE_JOURNAL)
    with open(TRADE_JOURNAL, "a", newline="") as f:
        writer = csv.writer(f)
        if not journal_exists:
            writer.writerow(["timestamp", "action", "pair", "lots", "price", "sl", "tp", "reason"])
        writer.writerow([datetime.now().isoformat(), action, pair, lots, price, sl, tp, reason])
