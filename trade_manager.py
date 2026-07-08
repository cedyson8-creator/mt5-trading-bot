import MetaTrader5 as mt5
from config import DRY_RUN
from logger import get_logger, log_trade
from risk_manager import check_spread, check_daily_loss, check_position_limits, calculate_sl_tp, calculate_position_size


class TradeManager:
    def __init__(self, connector):
        self.connector = connector
        self.logger = get_logger()
        self.daily_start_balance = None

    def set_daily_balance(self, balance):
        self.daily_start_balance = balance

    def execute_signal(self, signal, pair, rates):
        if signal not in ("buy", "sell"):
            return

        if not self.connector.is_connected():
            self.logger.warning("Not connected to MT5, skipping trade")
            return

        symbol_info = mt5.symbol_info(pair)
        if symbol_info is None:
            self.logger.error(f"Symbol info not found for {pair}")
            return

        if not check_spread(symbol_info):
            self.logger.warning(f"Spread too high for {pair}, skipping")
            return

        ok, msg = check_position_limits(self.connector, pair)
        if not ok:
            self.logger.info(f"Position limit: {msg}")
            return

        current_price = rates[-1][4]
        sl, tp = calculate_sl_tp(rates, current_price, signal)
        if sl is None or tp is None:
            self.logger.warning("Could not calculate SL/TP, skipping")
            return

        account_info = self.connector.get_account_summary()
        if account_info is None:
            return

        if not check_daily_loss(self.daily_start_balance, account_info["equity"]):
            self.logger.warning(f"Daily loss limit reached ({account_info['equity']:.2f} vs start {self.daily_start_balance:.2f}), no new trades")
            return

        lots = calculate_position_size(account_info["balance"], current_price, sl, symbol_info)
        if lots <= 0:
            self.logger.warning(f"Calculated lot size <= 0 for {pair}")
            return

        if DRY_RUN:
            self._dry_run_trade(signal, pair, lots, current_price, sl, tp)
        else:
            self._live_trade(signal, pair, lots, current_price, sl, tp, symbol_info)

    def _dry_run_trade(self, signal, pair, lots, price, sl, tp):
        action = "BUY" if signal == "buy" else "SELL"
        msg = f"[DRY-RUN] {action} {pair} {lots} lots @ {price} SL:{sl} TP:{tp}"
        self.logger.info(msg)
        log_trade(f"DRY_{action}", pair, lots, price, sl, tp)

    def _live_trade(self, signal, pair, lots, price, sl, tp, symbol_info):
        order_type = mt5.ORDER_TYPE_BUY if signal == "buy" else mt5.ORDER_TYPE_SELL
        action = "BUY" if signal == "buy" else "SELL"

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pair,
            "volume": lots,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 202406,
            "comment": "MT5Bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            self.logger.info(f"[LIVE] {action} {pair} {lots} lots @ {price} | Ticket: {result.order}")
            log_trade(f"LIVE_{action}", pair, lots, price, sl, tp, f"ticket={result.order}")
        else:
            err = result.comment if result else "unknown"
            self.logger.error(f"[LIVE] Order failed for {pair}: {err}")
