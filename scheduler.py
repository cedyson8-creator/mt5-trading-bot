import time
import threading
from datetime import datetime
from config import (
    CHECK_INTERVAL_SECONDS, HEARTBEAT_INTERVAL_MINUTES, PAIRS, TIMEFRAME,
    STRATEGY, ML_TRAINING_BARS, ML_TRAINING_INTERVAL_SECONDS,
)
from ml_model import extract_features
from logger import get_logger
from strategy_engine import generate_signal
from risk_manager import check_daily_loss


class Scheduler:
    def __init__(self, connector, trade_manager, ml_model=None):
        self.connector = connector
        self.trade_manager = trade_manager
        self.ml_model = ml_model
        self.logger = get_logger()
        self.running = False
        self._thread = None
        self._heartbeat_counter = 0
        self._heartbeat_interval_ticks = max(1, int((HEARTBEAT_INTERVAL_MINUTES * 60) / CHECK_INTERVAL_SECONDS))
        self._training_counter = 0
        self._training_interval_ticks = max(1, int(ML_TRAINING_INTERVAL_SECONDS / CHECK_INTERVAL_SECONDS))
        self._initial_tick = True

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self.logger.info("Scheduler started — checking every {}s".format(CHECK_INTERVAL_SECONDS))

    def stop(self):
        self.running = False
        self.logger.info("Scheduler stopping...")

    def _run_loop(self):
        while self.running:
            try:
                self._tick()
            except Exception as e:
                self.logger.error(f"Scheduler error: {e}")
            time.sleep(CHECK_INTERVAL_SECONDS)

    def _tick(self):
        if not self.connector.is_connected():
            self.logger.warning("Connection lost, attempting reconnect...")
            if not self.connector.reconnect():
                return

        self._heartbeat_counter += 1
        if self._heartbeat_counter >= self._heartbeat_interval_ticks:
            self._heartbeat()
            self._heartbeat_counter = 0

        if STRATEGY == "ml" and self.ml_model and self.ml_model.trained:
            self.trade_manager.process_closed_trades()
            self._training_counter += 1
            if self._training_counter >= self._training_interval_ticks:
                self._retrain_ml()
                self._training_counter = 0

        self._check_and_trade()

    def _heartbeat(self):
        info = self.connector.get_account_summary()
        if info:
            self.logger.info(f"HEARTBEAT | Balance: {info['balance']:.2f} | "
                             f"Equity: {info['equity']:.2f} | "
                             f"Open P&L: {info['profit']:.2f}")
        else:
            self.logger.info("HEARTBEAT | Running")

    def _retrain_ml(self):
        self.logger.info("ML retrain cycle: fetching fresh data...")
        all_rates = []
        for pair in PAIRS:
            rates = self.connector.get_rates(pair, TIMEFRAME, bars=ML_TRAINING_BARS)
            if rates is not None and len(rates) > 500:
                all_rates.extend(rates)
        if len(all_rates) > 500:
            fb_count = self.ml_model.feedback_count()
            self.logger.info(f"Retraining with {fb_count} feedback samples")
            self.ml_model.train_with_feedback(all_rates)

    def _check_and_trade(self):
        for pair in PAIRS:
            rates = self.connector.get_rates(pair, TIMEFRAME, bars=500)
            if rates is None:
                continue

            if STRATEGY == "ml" and self.ml_model:
                signal, confidence = self.ml_model.predict(rates)
                if signal != "hold":
                    self.logger.info(f"{pair} ML signal: {signal.upper()} ({confidence:.0%})")
                    feats = extract_features(rates)
                    self.trade_manager.execute_signal(signal, pair, rates, feats)
            else:
                signal = generate_signal(rates)
                if signal != "hold":
                    self.logger.info(f"{pair} signal: {signal.upper()}")
                    self.trade_manager.execute_signal(signal, pair, rates)
