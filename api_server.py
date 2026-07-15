import json
import threading
import csv
from http.server import HTTPServer, BaseHTTPRequestHandler
import config
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
        path_map = {
            "/status": self._handle_status,
            "/trades": self._handle_trades,
            "/model": self._handle_model,
            "/config": self._handle_config,
        }
        handler = path_map.get(self.path)
        if handler:
            handler()
        else:
            self._json({"error": "not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _get_bot(self):
        return BotAPI.bot_ref or {}

    def _handle_status(self):
        bot = self._get_bot()
        connector = bot.get("connector")
        account = None
        positions = []
        connected = False
        if connector:
            try:
                account = connector.get_account_summary()
                connected = connector.is_connected()
                positions = connector.get_positions() or []
            except Exception:
                pass

        self._json({
            "status": "running" if connected else "disconnected",
            "strategy": config.STRATEGY,
            "pairs": config.PAIRS,
            "account": account,
            "open_positions": len(positions),
        })

    def _handle_trades(self):
        try:
            with open(config.TRADE_JOURNAL, "r", newline="") as f:
                reader = list(csv.reader(f))
            header = reader[0] if reader else []
            rows = reader[-51:] if reader else []
            self._json({"header": header, "trades": rows})
        except (FileNotFoundError, IndexError):
            self._json({"trades": []})

    def _handle_model(self):
        ml = self._get_bot().get("ml_model")
        if ml and getattr(ml, "trained", False):
            imp = ml.get_feature_importance() if hasattr(ml, "get_feature_importance") else {}
            top = dict(list(imp.items())[:10]) if imp else {}
            self._json({
                "trained": True,
                "accuracy": round(ml.training_accuracy, 4),
                "feedback_samples": len(getattr(ml, "feedback_buffer", [])),
                "open_tracked_trades": len(getattr(ml, "open_trades", {})),
                "top_features": top,
            })
        else:
            self._json({"trained": False})

    def _handle_config(self):
        from config import (
            TIMEFRAME_STR, RISK_PER_TRADE, ATR_PERIOD,
            RR_RATIO, MAX_CONCURRENT_POSITIONS, MAX_DAILY_LOSS_PCT,
            ML_CONFIDENCE_THRESHOLD, DRY_RUN,
        )
        self._json({
            "pairs": config.PAIRS,
            "timeframe": TIMEFRAME_STR,
            "strategy": config.STRATEGY,
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
    get_logger().info(f"API server running at http://localhost:{port}")
    return server
