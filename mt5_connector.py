import time
import MetaTrader5 as mt5
from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER
from logger import get_logger


class MT5Connector:
    def __init__(self):
        self.logger = get_logger()
        self.connected = False
        self.account_info = None

    def connect(self, max_retries=3, retry_delay=5):
        for attempt in range(1, max_retries + 1):
            if not mt5.initialize():
                self.logger.error(f"MT5 initialize failed (attempt {attempt}/{max_retries}): {mt5.last_error()}")
                time.sleep(retry_delay)
                continue

            terminal = mt5.terminal_info()
            info = mt5.account_info()

            if info and info.login == MT5_LOGIN:
                self.account_info = info
                self.connected = True
                self.logger.info(f"Connected to MT5 — Account: {self.account_info.login}, "
                                 f"Balance: {self.account_info.balance:.2f}, "
                                 f"Leverage: 1:{self.account_info.leverage}")
                if terminal and not terminal.trade_allowed:
                    self.logger.warning("Algo Trading is disabled in this MT5 session")
                return True

            authorized = mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
            if not authorized:
                self.logger.error(f"MT5 login failed (attempt {attempt}/{max_retries}): {mt5.last_error()}")
                mt5.shutdown()
                time.sleep(retry_delay)
                continue

            self.account_info = mt5.account_info()
            if self.account_info is None:
                self.logger.error(f"Failed to get account info (attempt {attempt}/{max_retries})")
                mt5.shutdown()
                time.sleep(retry_delay)
                continue

            self.connected = True
            self.logger.info(f"Connected to MT5 — Account: {self.account_info.login}, "
                             f"Balance: {self.account_info.balance:.2f}, "
                             f"Leverage: 1:{self.account_info.leverage}")
            return True

        self.connected = False
        return False

    def reconnect(self):
        self.logger.info("Attempting MT5 reconnection...")
        mt5.shutdown()
        time.sleep(2)
        return self.connect(max_retries=5, retry_delay=3)

    def is_connected(self):
        if not mt5.terminal_info():
            self.connected = False
        return self.connected

    def get_rates(self, symbol, timeframe, bars=500):
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
        if rates is None or len(rates) == 0:
            self.logger.warning(f"No rate data for {symbol}")
            return None
        return rates

    def get_account_summary(self):
        info = mt5.account_info()
        if info:
            return {
                "balance": info.balance,
                "equity": info.equity,
                "margin": info.margin,
                "free_margin": info.margin_free,
                "profit": info.profit,
                "leverage": info.leverage,
            }
        return None

    def get_positions(self, symbol=None):
        if symbol:
            return mt5.positions_get(symbol=symbol)
        return mt5.positions_get()

    def get_history_deals(self, date_from, date_to):
        try:
            return mt5.history_deals_get(date_from, date_to)
        except Exception as e:
            self.logger.error(f"Failed to fetch history deals: {e}")
            return None

    def validate_symbols(self, pairs, strict=False):
        valid_pairs = []
        warnings = []
        fatal_issues = []

        for pair in pairs:
            if not mt5.symbol_select(pair, True):
                msg = f"Invalid or unavailable symbol: {pair}"
                (fatal_issues if strict else warnings).append(msg)
                continue

            info = mt5.symbol_info(pair)
            if info is None:
                msg = f"Symbol info unavailable for {pair}"
                (fatal_issues if strict else warnings).append(msg)
                continue

            if getattr(info, "trade_mode", 0) == 0:
                msg = f"Trading is disabled for symbol {pair}"
                (fatal_issues if strict else warnings).append(msg)
                continue

            valid_pairs.append(pair)

        return valid_pairs, warnings, fatal_issues

    def startup_check(self, pairs, strict_symbols=False):
        issues = []
        terminal = mt5.terminal_info()
        account = mt5.account_info()

        if terminal is None:
            issues.append("MT5 terminal is not available")
        elif not terminal.trade_allowed:
            issues.append("Algo trading is disabled in the MT5 terminal")

        if account is None:
            issues.append("MT5 account info is unavailable")
        elif MT5_LOGIN and account.login != MT5_LOGIN:
            issues.append(f"Connected to account {account.login}, expected {MT5_LOGIN}")

        if strict_symbols:
            _, _, fatal_issues = self.validate_symbols(pairs, strict=True)
            issues.extend(fatal_issues)

        return issues

    def disconnect(self):
        mt5.shutdown()
        self.connected = False
        self.logger.info("Disconnected from MT5")
