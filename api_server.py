import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from config import PAIRS, STRATEGY
from logger import get_logger


class BotAPI(BaseHTTPRequestHandler):
    bot_ref = None

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def do_GET(self):
        if self.path == "/status":
            self._handle_status()
        elif self.path == "/trades":
            self._handle_trades()
        elif self.path == "/model":
            self._handle_model()
        elif self.path == "/config":
            self._handle_config()
        else:
            self._json({"error": "not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _handle_status(self):
        bot = BotAPI.bot_ref
        if not bot:
            self._json({"status": "no reference"})
            return
        info = bot.get("connector", lambda: None)()
        if info and callable(info):
            info = info()
        account = bot.get("trade_manager", lambda: None)()
        if account and callable(account):
            account = None
        self._json({
            "status": "running",
            "strategy": STRATEGY,
            "pairs": PAIRS,
        })

    def _handle_trades(self):
        try:
            with open("trade_journal.csv", "r") as f:
                lines = f.readlines()
            rows = [line.strip().split(",") for line in lines[-50:]]
            self._json({"trades": rows})
        except FileNotFoundError:
            self._json({"trades": []})

    def _handle_model(self):
        bot = BotAPI.bot_ref
        if not bot:
            self._json({"model": None})
            return
        ml = bot.get("ml_model")
        if ml and ml.trained:
            imp = ml.get_feature_importance()
            top = dict(list(imp.items())[:10]) if imp else {}
            self._json({
                "trained": True,
                "accuracy": ml.training_accuracy,
                "feedback_samples": len(ml.feedback_buffer),
                "open_tracked_trades": len(ml.open_trades),
                "top_features": top,
            })
        else:
            self._json({"trained": False})

    def _handle_config(self):
        from config import (
            PAIRS, TIMEFRAME_STR, STRATEGY, RISK_PER_TRADE, ATR_PERIOD,
            RR_RATIO, MAX_CONCURRENT_POSITIONS, MAX_DAILY_LOSS_PCT,
            ML_CONFIDENCE_THRESHOLD, DRY_RUN,
        )
        self._json({
            "pairs": PAIRS,
            "timeframe": TIMEFRAME_STR,
            "strategy": STRATEGY,
            "risk_per_trade": RISK_PER_TRADE,
            "atr_period": ATR_PERIOD,
            "rr_ratio": RR_RATIO,
            "max_positions": MAX_CONCURRENT_POSITIONS,
            "daily_loss_limit_pct": MAX_DAILY_LOSS_PCT,
            "ml_confidence": ML_CONFIDENCE_THRESHOLD,
            "dry_run": DRY_RUN,
        })

    def log_message(self, format, *args):
        pass


def start_api_server(bot_ref, port=8080):
    BotAPI.bot_ref = bot_ref
    server = HTTPServer(("0.0.0.0", port), BotAPI)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    get_logger().info(f"API server started on port {port}")
    return server
