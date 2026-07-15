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
    :root {
      color-scheme: dark;
      --bg: #07111d;
      --panel: rgba(14, 24, 40, 0.92);
      --panel-border: rgba(95, 126, 168, 0.24);
      --text: #e7effb;
      --muted: #98adca;
      --accent: #66e9b2;
      --warn: #ffcc7a;
      --danger: #ff8d8d;
      --shadow: 0 18px 50px rgba(0, 0, 0, 0.30);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Segoe UI, Arial, sans-serif;
      background:
        radial-gradient(circle at top left, rgba(82, 132, 255, 0.18), transparent 28%),
        radial-gradient(circle at top right, rgba(102, 233, 178, 0.13), transparent 24%),
        linear-gradient(180deg, #08101c 0%, #09131f 45%, #07111d 100%);
      color: var(--text);
      min-height: 100vh;
    }
    .wrap { max-width: 1200px; margin: 0 auto; padding: 28px 20px 36px; }
    .topbar {
      display:flex;
      gap:16px;
      align-items:flex-start;
      justify-content:space-between;
      flex-wrap:wrap;
      margin-bottom: 18px;
    }
    .hero {
      flex: 1 1 520px;
      background: linear-gradient(135deg, rgba(15,28,48,.94), rgba(13,23,37,.94));
      border:1px solid var(--panel-border);
      border-radius:20px;
      padding:22px;
      box-shadow: var(--shadow);
    }
    .brandline {
      display:flex;
      align-items:center;
      gap:12px;
      margin-bottom: 12px;
    }
    .logo {
      width: 44px;
      height: 44px;
      border-radius: 14px;
      background: linear-gradient(135deg, rgba(102,233,178,.22), rgba(82,132,255,.22));
      border:1px solid rgba(255,255,255,.10);
      display:grid;
      place-items:center;
      font-size: 22px;
    }
    .title { font-size: 30px; font-weight: 800; margin: 0 0 6px; letter-spacing: -0.02em; }
    .subtitle { color: var(--muted); line-height: 1.45; }
    .statusbox {
      flex: 0 1 320px;
      background: linear-gradient(135deg, rgba(18,30,50,.92), rgba(10,18,31,.92));
      border:1px solid var(--panel-border);
      border-radius:20px;
      padding:18px;
      box-shadow: var(--shadow);
      display:flex;
      flex-direction:column;
      gap:14px;
      min-width: 280px;
    }
    .pill {
      display:inline-block;
      padding:7px 11px;
      border-radius:999px;
      font-size:12px;
      font-weight:800;
      letter-spacing:.05em;
      text-transform:uppercase;
    }
    .ok { background: rgba(18, 59, 42, .95); color:#8df2b8; }
    .warn { background: rgba(59, 38, 18, .95); color:#ffd08a; }
    .bad { background: rgba(59, 18, 18, .95); color:#ffb0b0; }
    .mode-title { font-size: 18px; font-weight: 800; margin:0; }
    .mode-desc { color: var(--muted); font-size: 13px; line-height:1.45; }
    .mode-row { display:flex; gap:12px; align-items:center; flex-wrap:wrap; }
    .grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap:16px; margin-top:16px; }
    .card {
      background: var(--panel);
      border:1px solid var(--panel-border);
      border-radius:18px;
      padding:18px;
      box-shadow: var(--shadow);
    }
    .label { font-size:12px; text-transform:uppercase; letter-spacing:.09em; color:#89a0bd; margin-bottom:8px; }
    .value { font-size:24px; font-weight:800; word-break:break-word; }
    .muted { color: var(--muted); }
    .metric { display:flex; flex-direction:column; gap:6px; min-height: 90px; }
    .metric .value { font-size:26px; }
    button {
      border:0;
      border-radius:14px;
      padding:13px 18px;
      font-weight:800;
      cursor:pointer;
      transition: transform .08s ease, opacity .15s ease, filter .15s ease;
    }
    button:hover { filter: brightness(1.03); }
    button:active { transform: translateY(1px); }
    button:disabled { opacity: .55; cursor: not-allowed; }
    .primary { background: linear-gradient(135deg, #71efb9, #4fda9f); color:#082015; }
    .danger { background: linear-gradient(135deg, #ffcc7a, #ffad5f); color:#2a1600; }
    .ghost { background: rgba(32, 50, 77, .95); color:#e6eef8; border:1px solid rgba(255,255,255,.08); }
    pre { margin:0; white-space:pre-wrap; word-break:break-word; line-height:1.5; }
    table { width:100%; border-collapse:collapse; font-size:13px; }
    th, td { border-bottom:1px solid #22344b; padding:10px 6px; text-align:left; vertical-align:top; }
    th { color:#9cb0c9; font-weight:700; white-space:nowrap; }
    .row { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
    .space { margin-top:16px; }
    .footer {
      margin-top: 16px;
      display:flex;
      justify-content:space-between;
      gap:12px;
      flex-wrap:wrap;
      color: var(--muted);
      font-size: 12px;
    }
    .split { display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-top:16px; }
    @media (max-width: 820px) {
      .split { grid-template-columns: 1fr; }
      .hero, .statusbox { flex-basis: 100%; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <div class="hero">
        <div class="brandline">
          <div class="logo">⟠</div>
          <div>
            <div class="muted">Local operator console</div>
            <h1 class="title">MT5 Trading Bot Dashboard</h1>
          </div>
        </div>
        <div class="subtitle">
          Monitor live status, review the self-learning model, and switch between demo and live mode from one local page.
        </div>
        <div class="footer">
          <div>Runs locally on <span id="hostValue">127.0.0.1</span></div>
          <div>Last refresh: <span id="lastRefresh">—</span></div>
        </div>
      </div>

      <div class="statusbox">
        <div>
          <span id="modePill" class="pill warn">Loading...</span>
          <p class="mode-title" id="modeHeadline">Loading mode...</p>
          <div class="mode-desc" id="modeDesc">Checking runtime state.</div>
        </div>
        <div class="mode-row">
          <button id="modeButton" class="primary" onclick="toggleMode()">Loading...</button>
          <button class="ghost" onclick="refresh()">Refresh</button>
        </div>
      </div>
    </div>

    <div class="grid">
      <div class="card metric">
        <div class="label">Connection</div>
        <div id="connectionState" class="value">Loading...</div>
        <div class="muted">MT5 terminal and account status</div>
      </div>
      <div class="card metric">
        <div class="label">Account Balance</div>
        <div id="balanceValue" class="value">—</div>
        <div class="muted">Current account balance and equity</div>
      </div>
      <div class="card metric">
        <div class="label">Open Positions</div>
        <div id="positionsValue" class="value">—</div>
        <div class="muted">Live positions detected by the bot</div>
      </div>
      <div class="card metric">
        <div class="label">Self-Learning</div>
        <div id="mlValue" class="value">—</div>
        <div class="muted">Model training and feedback status</div>
      </div>
    </div>

    <div class="split space">
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

function setNotice(message, kind) {
  const el = document.getElementById("notice");
  el.textContent = message;
  el.style.color = kind === "bad" ? "#ffb0b0" : kind === "warn" ? "#ffd08a" : "#98adca";
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
  let status, config, model, trades;
  try {
    [status, config, model, trades] = await Promise.all([
      loadJson("/status"),
      loadJson("/config"),
      loadJson("/model"),
      loadJson("/trades"),
    ]);
  } catch (err) {
    setNotice(`Dashboard refresh failed: ${err.message || err}`, "bad");
    return;
  }

  const dryRun = !!config.dry_run;
  const connected = status.status === "running";
  setText("connectionState", connected ? "Connected" : "Disconnected");
  setText("balanceValue", status.account ? `${Number(status.account.balance).toFixed(2)} / ${Number(status.account.equity).toFixed(2)}` : "—");
  setText("positionsValue", String(status.open_positions ?? 0));
  const feedbackCount = model.feedback_samples ?? status.self_learning?.feedback_samples ?? 0;
  setText("mlValue", model.trained ? `Trained (${(model.accuracy * 100).toFixed(1)}%) • ${feedbackCount} feedback` : `Not trained • ${feedbackCount} feedback`);
  setText("pairsValue", Array.isArray(status.pairs) ? status.pairs.join(", ") : "—");
  setText("flagsValue", `Mode: ${modeText(dryRun)}\nLive unlock: ${config.allow_live_trading ? "enabled" : "disabled"}\nAPI server: ${config.api_enabled ? "enabled" : "disabled"}`);
  const pill = document.getElementById("modePill");
  pill.className = modeClass(dryRun);
  pill.textContent = modeText(dryRun);
  setText("modeHeadline", dryRun ? "Demo mode active" : "Live mode active");
  setText("modeDesc", dryRun
    ? "Orders are simulated. Use this to verify signals, pair selection, and tracking without sending live trades."
    : "Live orders are enabled. Keep the bot supervised and confirm the account, broker, and risk settings are correct.");
  const button = document.getElementById("modeButton");
  button.textContent = modeButtonText(dryRun);
  button.className = dryRun ? "primary" : "danger";
  button.disabled = false;
  setNotice(connected ? "Dashboard synced." : "MT5 is disconnected. Check the terminal, account, and credentials.", connected ? "ok" : "warn");

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

  setText("lastRefresh", new Date().toLocaleTimeString());
}

async function toggleMode() {
  const config = await loadJson("/config");
  const desired = !config.dry_run;
  if (!desired) {
    const proceed = confirm("Switch to live mode? This will allow real orders if ALLOW_LIVE_TRADING is enabled.");
    if (!proceed) {
      return;
    }
  }
  const res = await fetch("/mode", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dry_run: desired })
  });
  const data = await res.json();
  if (!res.ok) {
    setNotice(data.error || "Mode change failed", "bad");
    return;
  }
  setNotice(`Mode switched to ${data.mode}.`, "ok");
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
        current_positions = []
        connector = bot.get("connector")
        if connector:
            try:
                current_positions = connector.get_positions() or []
            except Exception:
                current_positions = []
        if not desired_dry_run and not config.ALLOW_LIVE_TRADING:
            self._json({"error": "Live trading is locked. Set ALLOW_LIVE_TRADING=true first."}, 403)
            return
        if not desired_dry_run and current_positions and config.DRY_RUN:
            self._json({
                "error": "Live mode switch blocked while positions are open. Close or reconcile positions first."
            }, 409)
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
        ml = bot.get("ml_model")
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
            "self_learning": {
                "trained": bool(ml and getattr(ml, "trained", False)),
                "feedback_samples": len(getattr(ml, "feedback_buffer", [])) if ml else 0,
            },
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
