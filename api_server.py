import json
import threading
import csv
from http.server import HTTPServer, BaseHTTPRequestHandler
import config
from logger import get_logger


class BotAPI(BaseHTTPRequestHandler):
    bot_ref = None
    dashboard_title = "MT5 Trading Bot Dashboard"

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def _html(self, html, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8", errors="ignore").strip()
        if not raw:
            return {}
        return json.loads(raw)

    def do_GET(self):
        path_map = {
            "/": self._handle_dashboard,
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

    def do_POST(self):
        if self.path == "/mode":
            self._handle_mode_update()
            return
        self._json({"error": "not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _handle_dashboard(self):
        self._html(self._dashboard_html())

    def _get_bot(self):
        return BotAPI.bot_ref or {}

    def _dashboard_html(self):
        return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>MT5 Trading Bot Dashboard</title>
  <style>
    :root { color-scheme: dark; }
    body { margin:0; font-family: Segoe UI, Arial, sans-serif; background:#08111f; color:#e6eef8; }
    .wrap { max-width: 1080px; margin: 0 auto; padding: 24px; }
    .hero { display:flex; gap:16px; align-items:flex-start; justify-content:space-between; flex-wrap:wrap; }
    .card { background:#0f1b2d; border:1px solid #20324d; border-radius:16px; padding:16px; box-shadow:0 10px 30px rgba(0,0,0,.25); }
    .grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap:16px; margin-top:16px; }
    .title { font-size: 28px; font-weight: 700; margin: 0 0 6px; }
    .muted { color:#9cb0c9; }
    .pill { display:inline-block; padding:6px 10px; border-radius:999px; font-size:12px; font-weight:700; letter-spacing:.04em; }
    .ok { background:#123b2a; color:#8df2b8; }
    .warn { background:#3b2612; color:#ffd08a; }
    .bad { background:#3b1212; color:#ff9d9d; }
    .label { font-size:12px; text-transform:uppercase; letter-spacing:.08em; color:#87a1bf; margin-bottom:6px; }
    .value { font-size:22px; font-weight:700; word-break:break-word; }
    button { border:0; border-radius:12px; padding:12px 16px; font-weight:700; cursor:pointer; }
    .primary { background:#5ee4a8; color:#082015; }
    .danger { background:#ffb45c; color:#2a1600; }
    .secondary { background:#20324d; color:#e6eef8; }
    pre { margin:0; white-space:pre-wrap; word-break:break-word; }
    table { width:100%; border-collapse:collapse; font-size:13px; }
    th, td { border-bottom:1px solid #20324d; padding:8px 6px; text-align:left; }
    th { color:#9cb0c9; font-weight:600; }
    .row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
    .space { margin-top:16px; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <div>
        <h1 class="title">MT5 Trading Bot Dashboard</h1>
        <div class="muted">Local control panel for monitoring and mode switching.</div>
      </div>
      <div class="row">
        <span id="modePill" class="pill warn">Loading...</span>
        <button id="modeButton" class="primary" onclick="toggleMode()">Loading...</button>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <div class="label">Connection</div>
        <div id="connectionState" class="value">Loading...</div>
        <div class="muted">MT5 terminal and account status</div>
      </div>
      <div class="card">
        <div class="label">Account Balance</div>
        <div id="balanceValue" class="value">—</div>
        <div class="muted">Current account balance and equity</div>
      </div>
      <div class="card">
        <div class="label">Open Positions</div>
        <div id="positionsValue" class="value">—</div>
        <div class="muted">Live positions detected by the bot</div>
      </div>
      <div class="card">
        <div class="label">Self-Learning</div>
        <div id="mlValue" class="value">—</div>
        <div class="muted">Model training and feedback status</div>
      </div>
    </div>

    <div class="grid space">
      <div class="card">
        <div class="label">Pairs</div>
        <pre id="pairsValue">—</pre>
      </div>
      <div class="card">
        <div class="label">Runtime Flags</div>
        <pre id="flagsValue">—</pre>
      </div>
    </div>

    <div class="card space">
      <div class="label">Recent Trades</div>
      <div style="overflow:auto;">
        <table>
          <thead>
            <tr>
              <th>Time</th><th>Pair</th><th>Action</th><th>Status</th><th>Profit</th><th>Ticket</th>
            </tr>
          </thead>
          <tbody id="tradesBody">
            <tr><td colspan="6" class="muted">Loading...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

<script>
async function loadJson(path) {
  const res = await fetch(path, { cache: "no-store" });
  return await res.json();
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function modeText(dryRun) {
  return dryRun ? "DEMO MODE" : "LIVE MODE";
}

function modeButtonText(dryRun) {
  return dryRun ? "Switch to Live" : "Switch to Demo";
}

function modeClass(dryRun) {
  return dryRun ? "pill warn" : "pill ok";
}

async function refresh() {
  const status = await loadJson("/status");
  const config = await loadJson("/config");
  const model = await loadJson("/model");
  const trades = await loadJson("/trades");

  const dryRun = !!config.dry_run;
  const connected = status.status === "running";
  setText("connectionState", connected ? "Connected" : "Disconnected");
  setText("balanceValue", status.account ? `${Number(status.account.balance).toFixed(2)} / ${Number(status.account.equity).toFixed(2)}` : "—");
  setText("positionsValue", String(status.open_positions ?? 0));
  setText("mlValue", model.trained ? `Trained (${(model.accuracy * 100).toFixed(1)}%)` : "Not trained");
  setText("pairsValue", Array.isArray(status.pairs) ? status.pairs.join(", ") : "—");
  setText("flagsValue", `Mode: ${modeText(dryRun)}\nLive unlock: ${config.allow_live_trading ? "enabled" : "disabled"}\nAPI server: ${config.api_enabled ? "enabled" : "disabled"}`);
  const pill = document.getElementById("modePill");
  pill.className = modeClass(dryRun);
  pill.textContent = modeText(dryRun);
  const button = document.getElementById("modeButton");
  button.textContent = modeButtonText(dryRun);
  button.className = dryRun ? "primary" : "danger";

  const body = document.getElementById("tradesBody");
  const rows = Array.isArray(trades.trades) ? trades.trades.slice(-10).reverse() : [];
  if (!rows.length) {
    body.innerHTML = '<tr><td colspan="6" class="muted">No trades logged yet</td></tr>';
  } else {
    body.innerHTML = rows.map(row => {
      const [time, action, pair, lots, price, sl, tp, reason, ticket, profit, balance, status] = row;
      return `<tr><td>${time ?? ""}</td><td>${pair ?? ""}</td><td>${action ?? ""}</td><td>${status ?? ""}</td><td>${profit ?? ""}</td><td>${ticket ?? ""}</td></tr>`;
    }).join("");
  }
}

async function toggleMode() {
  const config = await loadJson("/config");
  const desired = !config.dry_run;
  const res = await fetch("/mode", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dry_run: desired })
  });
  const data = await res.json();
  if (!res.ok) {
    alert(data.error || "Mode change failed");
    return;
  }
  await refresh();
}

refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
        """

    def _handle_mode_update(self):
        bot = self._get_bot()
        trade_manager = bot.get("trade_manager")

        try:
            payload = self._read_json_body()
        except Exception:
            self._json({"error": "invalid json"}, 400)
            return

        if not isinstance(payload, dict) or "dry_run" not in payload:
            self._json({"error": "dry_run field is required"}, 400)
            return

        desired_dry_run = bool(payload.get("dry_run"))
        if not desired_dry_run and not config.ALLOW_LIVE_TRADING:
            self._json({"error": "Live trading is locked. Set ALLOW_LIVE_TRADING=true first."}, 403)
            return

        config.DRY_RUN = desired_dry_run
        get_logger().warning(f"Runtime mode changed via dashboard: {'DRY_RUN' if desired_dry_run else 'LIVE'}")

        if trade_manager and hasattr(trade_manager, "write_open_trades_snapshot"):
            try:
                trade_manager.write_open_trades_snapshot()
            except Exception:
                pass

        self._json({
            "ok": True,
            "dry_run": config.DRY_RUN,
            "mode": "DEMO" if config.DRY_RUN else "LIVE",
        })

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
            ML_CONFIDENCE_THRESHOLD, DRY_RUN, ALLOW_LIVE_TRADING, ENABLE_API_SERVER,
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
            "allow_live_trading": ALLOW_LIVE_TRADING,
            "api_enabled": ENABLE_API_SERVER,
        })

    def log_message(self, format, *args):
        pass


def start_api_server(bot_ref, port=8080):
    return start_api_server_with_host(bot_ref, host=config.API_HOST, port=port)


def start_api_server_with_host(bot_ref, host="127.0.0.1", port=8080):
    BotAPI.bot_ref = bot_ref
    server = HTTPServer((host, port), BotAPI)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    if host not in ("127.0.0.1", "localhost", "::1"):
        get_logger().warning(f"API server bound to non-local host {host}:{port}")
    get_logger().info(f"API server running at http://{host}:{port}")
    return server
