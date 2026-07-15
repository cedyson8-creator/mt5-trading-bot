import time
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import config
from logger import get_logger, log_trade
from trade_persistence import (
    serialize_features,
    deserialize_features,
    read_trade_journal,
    extract_closed_ids,
    write_open_trades_snapshot,
    build_snapshot_row,
)
from risk_manager import check_spread, check_daily_loss, check_position_limits, calculate_sl_tp, calculate_position_size, _atr, calculate_trailing_sl
from notifier import notify_trade_open, notify_trade_close


class TradeManager:
    def __init__(self, connector, ml_model=None):
        self.connector = connector
        self.ml_model = ml_model
        self.logger = get_logger()
        self.daily_start_balance = None
        self._last_check_time = 0
        self._closed_trades_logged = set()
        self._stale_open_warned = set()

    def set_daily_balance(self, balance):
        self.daily_start_balance = balance

    def set_ml_model(self, ml_model):
        self.ml_model = ml_model

    @staticmethod
    def _normalize_price(price, digits):
        try:
            return round(float(price), int(digits))
        except Exception:
            return price

    @staticmethod
    def _signal_from_action(action):
        action = (action or "").upper()
        if action.endswith("BUY"):
            return "buy"
        if action.endswith("SELL"):
            return "sell"
        return ""

    @staticmethod
    def _deal_profit(deal):
        return (
            float(getattr(deal, "profit", 0) or 0)
            + float(getattr(deal, "swap", 0) or 0)
            + float(getattr(deal, "commission", 0) or 0)
            + float(getattr(deal, "fee", 0) or 0)
        )

    @staticmethod
    def _restored_trade_entry(row, signal, features, entry_time):
        return {
            "features": features,
            "signal": signal,
            "entry_time": entry_time,
            "pair": row.get("pair", ""),
            "price": float(row.get("price") or 0) if row.get("price") else 0,
            "sl": float(row.get("sl") or 0) if row.get("sl") else 0,
            "tp": float(row.get("tp") or 0) if row.get("tp") else 0,
            "lots": float(row.get("lots") or 0) if row.get("lots") else 0,
            "restored": True,
        }

    @staticmethod
    def _is_order_success(result):
        if not result:
            return False
        success_codes = {
            code for code in (
                getattr(mt5, "TRADE_RETCODE_DONE", None),
                getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", None),
            )
            if code is not None
        }
        return result.retcode in success_codes

    def _log_close(self, trade_id, pair, signal, lots, price, sl, tp, profit, balance, reason="", ticket=""):
        if trade_id in self._closed_trades_logged:
            return
        action = f"CLOSE_{signal.upper()}" if signal in ("buy", "sell") else "CLOSE"
        log_trade(
            action,
            pair,
            lots,
            price,
            sl,
            tp,
            reason=reason,
            ticket=ticket,
            profit=round(float(profit), 2) if profit is not None else "",
            balance=round(float(balance), 2) if balance is not None else "",
            status="CLOSE",
        )
        self._closed_trades_logged.add(trade_id)

    def bootstrap_trade_state(self, history_days=config.HISTORY_BACKFILL_DAYS):
        try:
            journal_rows = read_trade_journal(config.TRADE_JOURNAL)
        except Exception as e:
            self.logger.warning(f"Could not read trade journal for recovery: {e}")
            return
        if not journal_rows:
            return

        self._closed_trades_logged.update(extract_closed_ids(journal_rows))
        self._restore_open_ml_trades(journal_rows)
        self.reconcile_open_trades()
        self._backfill_missing_closes(journal_rows, history_days=history_days)

    def reconcile_open_trades(self):
        if not self.ml_model or not hasattr(self.ml_model, "open_trades"):
            return

        positions = self.connector.get_positions() or []
        position_map = {str(p.ticket): p for p in positions}
        tracked_ids = list(self.ml_model.open_trades.keys())

        removed = 0
        for trade_id in tracked_ids:
            trade_key = str(trade_id)
            if trade_key in position_map:
                continue
            if trade_key.startswith("dry_"):
                continue

            self.logger.warning(f"Tracked trade {trade_id} is not present in MT5 positions; marking closed")
            self.ml_model.open_trades.pop(trade_id, None)
            removed += 1

        if removed:
            self.logger.info(f"Reconciled {removed} missing tracked trades against live MT5 positions")

        tracked_ids = {str(k) for k in self.ml_model.open_trades.keys()}
        untracked = []
        for ticket, pos in position_map.items():
            if ticket not in tracked_ids:
                untracked.append(ticket)
        if untracked:
            self.logger.warning(f"{len(untracked)} open MT5 positions are not being tracked by ML: {', '.join(untracked[:5])}")

    def write_open_trades_snapshot(self, path=config.OPEN_TRADES_SNAPSHOT):
        if not self.ml_model or not hasattr(self.ml_model, "open_trades"):
            return False

        positions = {str(p.ticket): p for p in (self.connector.get_positions() or [])}
        snapshot = []
        for trade_id, entry in self.ml_model.open_trades.items():
            pos = positions.get(str(trade_id))
            snapshot.append(build_snapshot_row(trade_id, entry, pos))

        try:
            write_open_trades_snapshot(path, snapshot)
            self.logger.info(f"Wrote open-trades snapshot to {path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to write open-trades snapshot: {e}")
            return False

    def _restore_open_ml_trades(self, journal_rows):
        if not self.ml_model or not hasattr(self.ml_model, "open_trades"):
            return

        positions = self.connector.get_positions() or []
        current_positions = {str(p.ticket): p for p in positions}

        restored = 0
        for row in journal_rows:
            status = (row.get("status") or "").upper()
            ticket = str(row.get("ticket") or "").strip()
            if status != "OPEN" or not ticket or ticket in self.ml_model.open_trades:
                continue
            if ticket not in current_positions:
                continue

            action = row.get("action", "")
            signal = self._signal_from_action(action)
            if signal not in ("buy", "sell"):
                continue

            features = deserialize_features(row.get("features"))
            if not features:
                features = {
                    "price": float(row.get("price") or 0),
                    "sl": float(row.get("sl") or 0) if row.get("sl") else 0,
                    "tp": float(row.get("tp") or 0) if row.get("tp") else 0,
                    "pair": row.get("pair", ""),
                    "lots": float(row.get("lots") or 0),
                }

            entry_time_raw = row.get("timestamp")
            try:
                entry_time = datetime.fromisoformat(entry_time_raw).timestamp() if entry_time_raw else time.time()
            except Exception:
                entry_time = time.time()

            self.ml_model.open_trades[ticket] = self._restored_trade_entry(row, signal, features, entry_time)
            restored += 1

        if restored:
            self.logger.info(f"Restored {restored} open ML trades from journal")

    def _backfill_missing_closes(self, journal_rows, history_days=config.HISTORY_BACKFILL_DAYS):
        if history_days <= 0:
            return

        open_rows = {
            str(row.get("ticket") or "").strip(): row
            for row in journal_rows
            if (row.get("status") or "").upper() == "OPEN" and str(row.get("ticket") or "").strip()
        }
        current_positions = {str(p.ticket) for p in (self.connector.get_positions() or [])}

        date_to = datetime.now()
        date_from = date_to - timedelta(days=history_days)
        deals = self.connector.get_history_deals(date_from, date_to)
        if not deals:
            return

        backfilled = 0
        account = self.connector.get_account_summary()
        for deal in deals:
            if getattr(deal, "magic", None) != 202406:
                continue
            if getattr(deal, "entry", None) != mt5.DEAL_ENTRY_OUT:
                continue

            position_id = getattr(deal, "position_id", 0) or getattr(deal, "order", 0) or getattr(deal, "ticket", 0)
            ticket = str(position_id)
            if not ticket or ticket in self._closed_trades_logged or ticket in current_positions:
                continue

            row = open_rows.get(ticket, {})
            pair = row.get("pair") or getattr(deal, "symbol", "")
            deal_type = getattr(deal, "type", None)
            signal = self._signal_from_action(row.get("action")) or (
                "buy" if deal_type == 0 else "sell" if deal_type == 1 else ""
            )
            lots = row.get("lots") or getattr(deal, "volume", 0) or 0
            price = getattr(deal, "price", 0) or row.get("price", 0) or 0
            sl = row.get("sl", "")
            tp = row.get("tp", "")
            profit = self._deal_profit(deal)

            if self.ml_model and ticket in self.ml_model.open_trades:
                self.ml_model.close_trade(ticket, profit)

            self._log_close(
                ticket,
                pair,
                signal,
                lots,
                price,
                sl,
                tp,
                profit,
                account["balance"] if account else "",
                reason="history-backfill",
                ticket=str(getattr(deal, "ticket", ticket)),
            )
            backfilled += 1

        if backfilled:
            self.logger.info(f"Backfilled {backfilled} closed trades from MT5 history")

    def process_closed_trades(self):
        if not self.ml_model or not self.ml_model.open_trades:
            return

        open_tickets = set()
        positions = self.connector.get_positions()
        if positions:
            open_tickets = {p.ticket for p in positions}

        now = time.time()
        max_age_seconds = config.ML_MAX_TRADE_AGE_HOURS * 3600

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
                    if trade_id not in self._stale_open_warned:
                        self.logger.warning(f"Live trade {trade_id} is stale but still open; leaving it to the broker")
                        self._stale_open_warned.add(trade_id)
                    continue
                if not is_stale:
                    history = mt5.history_deals_get(ticket=trade_id)
                    if history and len(history) > 0:
                        profit = sum(self._deal_profit(deal) for deal in history)
                        self.ml_model.close_trade(trade_id, profit)
                        entry_pair = entry.get("pair", "")
                        entry_signal = entry.get("signal", "")
                        entry_lots = entry.get("lots", 0)
                        entry_price = entry.get("price", 0)
                        entry_sl = entry.get("sl", "")
                        entry_tp = entry.get("tp", "")
                        account = self.connector.get_account_summary()
                        self._log_close(
                            trade_id,
                            entry_pair,
                            entry_signal,
                            entry_lots,
                            entry_price,
                            entry_sl,
                            entry_tp,
                            profit,
                            account["balance"] if account else "",
                            reason="history-deal-close",
                            ticket=str(trade_id),
                        )
                        if account:
                            notify_trade_close(entry_pair, entry_signal or "buy", profit, account["balance"])

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
                    account = self.connector.get_account_summary()
                    self._log_close(
                        trade_id,
                        pair,
                        direction or "",
                        entry.get("lots", 0),
                        price,
                        sl,
                        tp,
                        profit_dollars,
                        account["balance"] if account else "",
                        reason="dry-hit" if not is_stale else "dry-stale",
                        ticket=trade_id,
                    )
                    if account:
                        notify_trade_close(pair, direction or "buy", profit_dollars, account["balance"])
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
        digits = getattr(symbol_info, "digits", 5) or 5
        sl, tp = calculate_sl_tp(rates, current_price, signal, digits=digits)
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

        if config.DRY_RUN:
            opened = self._dry_run_trade(signal, pair, lots, current_price, sl, tp, features)
        else:
            opened = self._live_trade(signal, pair, lots, current_price, sl, tp, symbol_info, features)

        if opened:
            notify_trade_open(signal, pair, lots, current_price, sl, tp)

    def _dry_run_trade(self, signal, pair, lots, price, sl, tp, features=None):
        action = "BUY" if signal == "buy" else "SELL"
        msg = f"[DRY-RUN] {action} {pair} {lots} lots @ {price} SL:{sl} TP:{tp}"
        self.logger.info(msg)
        log_trade(
            f"DRY_{action}",
            pair,
            lots,
            price,
            sl,
            tp,
            status="OPEN",
            features=serialize_features(features),
        )
        import uuid
        tid = f"dry_{uuid.uuid4().hex[:8]}"
        if features and self.ml_model:
            self.ml_model.record_open_trade(tid, features, signal)
            if hasattr(self.ml_model, 'open_trades') and tid in self.ml_model.open_trades:
                self.ml_model.open_trades[tid].update({
                    "price": price, "sl": sl, "tp": tp, "pair": pair, "lots": lots
                })
            self.logger.info(f"ML feedback tracking started for {tid} (dry-run)")
        return True

    def _live_trade(self, signal, pair, lots, price, sl, tp, symbol_info, features=None):
        order_type = mt5.ORDER_TYPE_BUY if signal == "buy" else mt5.ORDER_TYPE_SELL
        action = "BUY" if signal == "buy" else "SELL"

        tick = mt5.symbol_info_tick(pair)
        if tick is None:
            self.logger.error(f"Failed to get tick for {pair}")
            return False

        live_price = tick.ask if signal == "buy" else tick.bid
        price_offset = live_price - price
        live_sl = sl + price_offset
        live_tp = tp + price_offset
        digits = getattr(symbol_info, "digits", 5) or 5
        point = getattr(symbol_info, "point", 0) or 0
        stops_level = getattr(symbol_info, "trade_stops_level", 0) or 0
        min_stop_distance = stops_level * point
        live_price = self._normalize_price(live_price, digits)
        live_sl = self._normalize_price(live_sl, digits)
        live_tp = self._normalize_price(live_tp, digits)

        if min_stop_distance > 0:
            if abs(live_price - live_sl) < min_stop_distance or abs(live_price - live_tp) < min_stop_distance:
                self.logger.warning(
                    f"{pair} stops too close for broker rules "
                    f"(min {min_stop_distance:.{digits}f}); skipping order"
                )
                return False

        self.logger.info(f"{pair} live={live_price} close={price} sl={live_sl} tp={live_tp}")

        filling_options = [mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_IOC, 64]
        filling_mode = getattr(symbol_info, "filling_mode", 0)

        if filling_mode & 1:
            filling_options.insert(0, mt5.ORDER_FILLING_IOC)
        if filling_mode & 2:
            filling_options.insert(0, mt5.ORDER_FILLING_FOK)
        if filling_mode & 64:
            filling_options.insert(0, 64)

        result = None
        last_err = None
        for type_filling in filling_options:
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pair,
                "volume": lots,
                "type": order_type,
                "price": live_price,
                "sl": live_sl,
                "tp": live_tp,
                "deviation": 20,
                "magic": 202406,
                "comment": "MT5Bot",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": type_filling,
            }
            result = mt5.order_send(request)
            if self._is_order_success(result):
                break
            last_err = f"retcode={getattr(result, 'retcode', 'unknown')} comment={getattr(result, 'comment', 'unknown')}" if result else "unknown"

        if self._is_order_success(result):
            self.logger.info(f"[LIVE] {action} {pair} {lots} lots @ {live_price} | Ticket: {result.order}")
            log_trade(
                f"LIVE_{action}",
                pair,
                lots,
                live_price,
                live_sl,
                live_tp,
                reason=f"ticket={result.order}",
                ticket=str(result.order),
                status="OPEN",
                features=serialize_features(features),
            )
            if features and self.ml_model:
                self.ml_model.record_open_trade(result.order, features, signal)
                if hasattr(self.ml_model, 'open_trades') and result.order in self.ml_model.open_trades:
                    self.ml_model.open_trades[result.order].update({
                        "price": live_price, "sl": live_sl, "tp": live_tp, "pair": pair, "lots": lots
                    })
                self.logger.info(f"ML feedback tracking started for ticket {result.order}")
            return True
        else:
            self.logger.error(f"[LIVE] Order failed for {pair}: {last_err}")
            return False

    def update_trailing_stops(self):
        if config.DRY_RUN:
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

                digits = getattr(mt5.symbol_info(pos.symbol), "digits", 5) or 5
                new_sl = calculate_trailing_sl(pos, current_price, atr_val, digits=digits)
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
                if self._is_order_success(result):
                    self.logger.info(f"Trail SL {pos.symbol} ticket {pos.ticket}: {pos.sl} -> {new_sl}")
                else:
                    self.logger.warning(f"Trail SL failed for {pos.ticket}: retcode={getattr(result, 'retcode', 'unknown')} comment={getattr(result, 'comment', 'unknown') if result else 'unknown'}")

            except Exception as e:
                self.logger.error(f"Trailing stop error for {pos.symbol}: {e}")
