import time
import MetaTrader5 as mt5
from config import DRY_RUN, STRATEGY, ML_MAX_TRADE_AGE_HOURS
from logger import get_logger, log_trade
from risk_manager import check_spread, check_daily_loss, check_position_limits, calculate_sl_tp, calculate_position_size, _atr, calculate_trailing_sl
from notifier import notify_trade_open, notify_trade_close


class TradeManager:
    def __init__(self, connector, ml_model=None):
        self.connector = connector
        self.ml_model = ml_model
        self.logger = get_logger()
        self.daily_start_balance = None
        self._last_check_time = 0

    def set_daily_balance(self, balance):
        self.daily_start_balance = balance

    def set_ml_model(self, ml_model):
        self.ml_model = ml_model

    def process_closed_trades(self):
        if not self.ml_model or not self.ml_model.open_trades:
            return

        open_tickets = set()
        positions = self.connector.get_positions()
        if positions:
            open_tickets = {p.ticket for p in positions}

        now = time.time()
        max_age_seconds = ML_MAX_TRADE_AGE_HOURS * 3600

        for trade_id in sorted(self.ml_model.open_trades.keys(), key=str):
            entry = self.ml_model.open_trades.get(trade_id)
            if not entry:
                continue

            entry_time = entry.get("entry_time", 0)
            is_stale = (now - entry_time) > max_age_seconds if entry_time else False

            if isinstance(trade_id, int):
                if trade_id in open_tickets and not is_stale:
                    continue
                if trade_id in open_tickets and is_stale:
                    positions = self.connector.get_positions()
                    for p in positions or []:
                        if p.ticket == trade_id:
                            profit = p.profit
                            self.ml_model.close_trade(trade_id, profit)
                            if profit >= 0:
                                self.logger.info(f"ML auto-closed stale trade {trade_id} at profit ${profit:.2f}")
                            break
                    continue
                if not is_stale:
                    history = mt5.history_deals_get(ticket=trade_id)
                    if history and len(history) > 0:
                        profit = history[0].profit
                        self.ml_model.close_trade(trade_id, profit)

            elif isinstance(trade_id, str) and trade_id.startswith("dry_"):
                pair = entry.get("pair")
                direction = entry.get("signal")
                price = entry.get("price")
                sl = entry.get("sl")
                tp = entry.get("tp")

                if not pair:
                    continue

                current_rates = self.connector.get_rates(pair, mt5.TIMEFRAME_M1, bars=2)
                if current_rates is None or len(current_rates) < 2:
                    if is_stale:
                        self.ml_model.open_trades.pop(trade_id, None)
                        self.logger.info(f"Removed stale dry-run trade {trade_id} (no data)")
                    continue

                current_price = current_rates[-1][4]

                hit = False
                profit = 0
                if direction == "buy":
                    if current_price >= tp:
                        profit = abs(tp - price)
                        hit = True
                    elif current_price <= sl:
                        profit = -abs(price - sl)
                        hit = True
                    elif is_stale:
                        profit = (current_price - price)
                        hit = True
                elif direction == "sell":
                    if current_price <= tp:
                        profit = abs(price - tp)
                        hit = True
                    elif current_price >= sl:
                        profit = -abs(sl - price)
                        hit = True
                    elif is_stale:
                        profit = (price - current_price)
                        hit = True

                if hit:
                    profit_dollars = profit * 10000 * 0.1
                    self.ml_model.close_trade(trade_id, profit_dollars)
                    if is_stale:
                        self.logger.info(f"ML auto-closed stale dry trade {trade_id} (P&L: ${profit_dollars:.2f})")

    def execute_signal(self, signal, pair, rates, features=None):
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

        lots = calculate_position_size(account_info["balance"], current_price, sl, symbol_info, pair)
        if lots <= 0:
            self.logger.warning(f"Calculated lot size <= 0 for {pair}")
            return

        if DRY_RUN:
            self._dry_run_trade(signal, pair, lots, current_price, sl, tp, features)
        else:
            self._live_trade(signal, pair, lots, current_price, sl, tp, symbol_info, features)
        notify_trade_open(signal, pair, lots, current_price, sl, tp)

    def _dry_run_trade(self, signal, pair, lots, price, sl, tp, features=None):
        action = "BUY" if signal == "buy" else "SELL"
        msg = f"[DRY-RUN] {action} {pair} {lots} lots @ {price} SL:{sl} TP:{tp}"
        self.logger.info(msg)
        log_trade(f"DRY_{action}", pair, lots, price, sl, tp)
        import uuid
        tid = f"dry_{uuid.uuid4().hex[:8]}"
        if features and self.ml_model:
            self.ml_model.record_open_trade(tid, features, signal)
            if hasattr(self.ml_model, 'open_trades') and tid in self.ml_model.open_trades:
                self.ml_model.open_trades[tid].update({
                    "price": price, "sl": sl, "tp": tp, "pair": pair
                })
            self.logger.info(f"ML feedback tracking started for {tid} (dry-run)")

    def _live_trade(self, signal, pair, lots, price, sl, tp, symbol_info, features=None):
        order_type = mt5.ORDER_TYPE_BUY if signal == "buy" else mt5.ORDER_TYPE_SELL
        action = "BUY" if signal == "buy" else "SELL"

        filling_mode = getattr(symbol_info, "filling_mode", 1)
        if filling_mode & 2:
            type_filling = mt5.ORDER_FILLING_FOK
        elif filling_mode & 1:
            type_filling = mt5.ORDER_FILLING_IOC
        else:
            type_filling = mt5.ORDER_FILLING_FOK

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
            "type_filling": type_filling,
        }

        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            self.logger.info(f"[LIVE] {action} {pair} {lots} lots @ {price} | Ticket: {result.order}")
            log_trade(f"LIVE_{action}", pair, lots, price, sl, tp, f"ticket={result.order}")
            if features and self.ml_model:
                self.ml_model.record_open_trade(result.order, features, signal)
                self.logger.info(f"ML feedback tracking started for ticket {result.order}")
        else:
            err = result.comment if result else "unknown"
            self.logger.error(f"[LIVE] Order failed for {pair}: {err}")

    def update_trailing_stops(self):
        if DRY_RUN:
            return
        if not self.connector.is_connected():
            return

        positions = self.connector.get_positions()
        if not positions:
            return

        for pos in positions:
            try:
                rates = self.connector.get_rates(pos.symbol, mt5.TIMEFRAME_M5, bars=50)
                if rates is None or len(rates) < 20:
                    continue

                atr_val = _atr(rates)
                if atr_val is None or atr_val == 0:
                    continue

                current_price = mt5.symbol_info_tick(pos.symbol).ask if pos.type == 0 else mt5.symbol_info_tick(pos.symbol).bid
                if current_price is None or current_price == 0:
                    continue

                new_sl = calculate_trailing_sl(pos, current_price, atr_val)
                if new_sl is None:
                    continue

                if pos.sl and abs(pos.sl - new_sl) / pos.sl < 0.0001:
                    continue

                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": pos.symbol,
                    "position": pos.ticket,
                    "sl": new_sl,
                    "tp": pos.tp,
                    "deviation": 10,
                    "magic": 202406,
                    "comment": "trail",
                }
                result = mt5.order_send(request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    self.logger.info(f"Trail SL {pos.symbol} ticket {pos.ticket}: {pos.sl} -> {new_sl}")
                else:
                    self.logger.warning(f"Trail SL failed for {pos.ticket}: {result.comment if result else 'unknown'}")

            except Exception as e:
                self.logger.error(f"Trailing stop error for {pos.symbol}: {e}")
