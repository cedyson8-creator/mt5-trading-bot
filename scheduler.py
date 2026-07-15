import time
import threading
import MetaTrader5 as mt5
import config
from ml_model import extract_features
from logger import get_logger
from strategy_engine import generate_signal, mtf_filter
from notifier import notify_heartbeat, notify_startup


TF_MAP = {
    "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


class Scheduler:
    def __init__(self, connector, trade_manager, ml_model=None):
        self.connector = connector
        self.trade_manager = trade_manager
        self.ml_model = ml_model
        self.logger = get_logger()
        self.running = False
        self._thread = None
        self._heartbeat_counter = 0
        self._heartbeat_interval_ticks = max(1, int((config.HEARTBEAT_INTERVAL_MINUTES * 60) / config.CHECK_INTERVAL_SECONDS))
        self._training_counter = 0
        self._training_interval_ticks = max(1, int(config.ML_TRAINING_INTERVAL_SECONDS / config.CHECK_INTERVAL_SECONDS))
        self._trail_counter = 0
        self._trail_interval_ticks = max(1, int(config.TRAILING_CHECK_INTERVAL * 60 / config.CHECK_INTERVAL_SECONDS))

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.logger.info("Scheduler started â€” checking every {}s".format(config.CHECK_INTERVAL_SECONDS))
        notify_startup()

    def stop(self):
        self.running = False
        self.logger.info("Scheduler stopping...")

    def _run_loop(self):
        while self.running:
            try:
                self._tick()
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
            time.sleep(config.CHECK_INTERVAL_SECONDS)

    def _tick(self):
        if not self.connector.is_connected():
            self.logger.warning("Connection lost, attempting reconnect...")
            if not self.connector.reconnect():
                return

        self._heartbeat_counter += 1
        if self._heartbeat_counter >= self._heartbeat_interval_ticks:
            self._heartbeat()
            self._heartbeat_counter = 0

        self._trail_counter += 1
        if self._trail_counter >= self._trail_interval_ticks:
            self.trade_manager.update_trailing_stops()
            self._trail_counter = 0

        if config.STRATEGY == "ml" and self.ml_model and self.ml_model.trained:
            self.trade_manager.process_closed_trades()
            self._training_counter += 1
            if self._training_counter >= self._training_interval_ticks:
                self._retrain_ml()
                self._training_counter = 0

        self._check_and_trade()

    def _heartbeat(self):
        info = self.connector.get_account_summary()
        positions = self.connector.get_positions()
        open_count = len(positions) if positions else 0
        if info:
            self.logger.info(f"HEARTBEAT | Balance: {info['balance']:.2f} | "
                             f"Equity: {info['equity']:.2f} | "
                             f"Open P&L: {info['profit']:.2f} | Positions: {open_count}")
            notify_heartbeat(info["balance"], info["equity"], info["profit"], open_count)
        else:
            self.logger.info("HEARTBEAT | Running")

    def _retrain_ml(self):
        self.logger.info("ML retrain cycle: fetching fresh data...")
        all_rates = []
        for pair in config.PAIRS:
            rates = self.connector.get_rates(pair, config.TIMEFRAME, bars=config.ML_TRAINING_BARS)
            if rates is not None and len(rates) > 500:
                all_rates.extend(rates)
        if len(all_rates) > 500:
            fb_count = self.ml_model.feedback_count()
            self.logger.info(f"Retraining with {fb_count} feedback samples")
            self.ml_model.train_with_feedback(all_rates)

    def _check_and_trade(self):
        traded = False
        for pair in config.PAIRS:
            rates = self.connector.get_rates(pair, config.TIMEFRAME, bars=500)
            if rates is None:
                continue

            higher_rates = None
            if config.MTF_ENABLED:
                higher_tf = TF_MAP.get(config.MTF_HIGHER_TF, mt5.TIMEFRAME_H1)
                higher_rates = self.connector.get_rates(pair, higher_tf, bars=config.MTF_MIN_BARS)

            if config.STRATEGY == "ml" and self.ml_model:
                signal, confidence = self.ml_model.predict(rates)
                if signal != "hold":
                    if not mtf_filter(higher_rates, signal):
                        continue
                    self.logger.info(f"{pair} ML signal: {signal.upper()} ({confidence:.0%})")
                    feats = extract_features(rates)
                    self.trade_manager.execute_signal(signal, pair, rates, feats)
                    traded = True
            else:
                signal = generate_signal(rates)
                if signal != "hold":
                    if not mtf_filter(higher_rates, signal):
                        continue
                    self.logger.info(f"{pair} signal: {signal.upper()}")
                    self.trade_manager.execute_signal(signal, pair, rates)
                    traded = True

        if not traded:
            self.logger.info("Signal check complete â€” no trades this cycle")
