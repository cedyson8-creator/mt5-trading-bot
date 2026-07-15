import json
import threading
import csv
import os
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import config
from logger import get_logger

STARTUP_SHORTCUT_NAME = "MT5 Trading Bot Auto.lnk"
PowershellExe = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"


def _startup_shortcut_path():
    startup = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return startup / STARTUP_SHORTCUT_NAME


def _run_powershell_script(script_name, extra_args=None):
    script_path = Path(__file__).resolve().parent / script_name
    if not script_path.exists():
        return False, f"Missing script: {script_name}"

    args = [
        str(PowershellExe),
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", str(script_path),
    ]
    if extra_args:
        args.extend(extra_args)

    try:
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        output = (result.stdout or result.stderr or "").strip()
        return True, output
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        return False, detail


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
        if self.path == "/automation":
            self._handle_automation()
            return
        if self.path == "/emergency-stop":
            self._handle_emergency_stop()
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
    .sidebar {
      flex: 0 0 220px;
      background: linear-gradient(180deg, rgba(14, 24, 40, .96), rgba(10, 18, 31, .96));
      border:1px solid var(--panel-border);
      border-radius:20px;
      padding:18px;
      box-shadow: var(--shadow);
      display:flex;
      flex-direction:column;
      gap:10px;
      min-width: 220px;
    }
    .nav-title { font-size: 12px; text-transform:uppercase; letter-spacing:.08em; color:#8da5c4; margin-bottom:6px; }
    .nav-item {
      display:flex;
      justify-content:space-between;
      gap:10px;
      align-items:center;
      padding:10px 12px;
      border-radius:12px;
      background: rgba(255,255,255,.03);
      color: var(--text);
      text-decoration:none;
      font-size: 13px;
    }
    .nav-item:hover { background: rgba(255,255,255,.06); }
    .nav-kicker { color: var(--muted); font-size: 12px; }
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
    .mode-switch {
      display:inline-flex;
      align-items:center;
      gap:10px;
      justify-content:center;
      min-width: 168px;
    }
    .btn-icon {
      display:inline-grid;
      place-items:center;
      width: 22px;
      height: 22px;
      font-size: 18px;
      line-height: 1;
    }
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
    .chart-card { margin-top:16px; }
    .chart-wrap {
      width: 100%;
      overflow-x:auto;
      background: rgba(5, 10, 18, .45);
      border-radius: 16px;
      border: 1px solid rgba(255,255,255,.05);
      padding: 12px;
    }
    .chart { width: 100%; min-height: 220px; }
    .small { font-size: 12px; color: var(--muted); }
    .kpi-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap:12px; margin-top:12px; }
    .kpi {
      background: rgba(255,255,255,.03);
      border-radius: 14px;
      padding: 12px;
      border:1px solid rgba(255,255,255,.05);
    }
    .kpi .label { margin-bottom: 6px; }
    .kpi .value { font-size: 20px; }
    .emergency {
      width:100%;
      background: linear-gradient(135deg, #ff5a5a, #ff3030);
      color: white;
      border: 1px solid rgba(255,255,255,.10);
      box-shadow: 0 10px 28px rgba(255, 50, 50, .28);
    }
    @media (max-width: 820px) {
      .split { grid-template-columns: 1fr; }
      .hero, .statusbox { flex-basis: 100%; }
      .sidebar { flex-basis: 100%; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="topbar">
      <aside class="sidebar">
        <div class="nav-title">Navigation</div>
        <a class="nav-item" href="#overview">Overview <span class="nav-kicker">status</span></a>
        <a class="nav-item" href="#chart">Activity <span class="nav-kicker">trades</span></a>
        <a class="nav-item" href="#pairs">Pairs <span class="nav-kicker">basket</span></a>
        <a class="nav-item" href="#logs">Logs <span class="nav-kicker">journal</span></a>
        <a class="nav-item" href="#controls">Controls <span class="nav-kicker">mode</span></a>
      </aside>

      <div class="hero" id="overview">
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
          <span id="autoPill" class="pill warn" style="margin-left:8px;">Loading...</span>
          <p class="mode-title" id="modeHeadline">Loading mode...</p>
          <div class="mode-desc" id="modeDesc">Checking runtime state.</div>
        </div>
        <div class="mode-row">
          <button id="modeButton" class="primary mode-switch" onclick="toggleMode()">
            <span id="modeButtonIcon" class="btn-icon">☀</span>
            <span id="modeButtonLabel">Loading...</span>
          </button>
          <button class="ghost" onclick="refresh()">Refresh</button>
        </div>
        <div class="mode-row">
          <button id="autoButton" class="ghost" onclick="toggleAutomation()">Loading...</button>
        </div>
        <button class="emergency" onclick="emergencyStop()">Emergency Stop</button>
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

    <div class="card chart-card" id="chart">
      <div class="label">Trade Activity</div>
      <div class="small">Recent closed-trade P&amp;L and balance trend from the journal.</div>
      <div class="kpi-grid">
        <div class="kpi"><div class="label">Today P/L</div><div id="todayPl" class="value">—</div></div>
        <div class="kpi"><div class="label">Closed Trades</div><div id="closedTrades" class="value">—</div></div>
        <div class="kpi"><div class="label">Win Rate</div><div id="winRate" class="value">—</div></div>
        <div class="kpi"><div class="label">Open P/L</div><div id="openPl" class="value">—</div></div>
      </div>
      <div class="chart-wrap">
        <svg id="activityChart" class="chart" viewBox="0 0 900 240" preserveAspectRatio="none" role="img" aria-label="Trade activity chart"></svg>
      </div>
    </div>

    <div class="split space">
      <div class="card" id="pairs">
        <div class="label">Pairs</div>
        <pre id="pairsValue">—</pre>
      </div>
      <div class="card" id="controls">
        <div class="label">Runtime Flags</div>
        <pre id="flagsValue">—</pre>
      </div>
    </div>

    <div class="card space" id="logs">
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

function modeButtonIcon(dryRun) {
  return dryRun ? "☾" : "☀";
}

function modeClass(dryRun) {
  return dryRun ? "pill warn" : "pill ok";
}

function autoText(enabled) {
  return enabled ? "FULL AUTO ON" : "FULL AUTO OFF";
}

function autoButtonText(enabled) {
  return enabled ? "Disable Full Auto" : "Enable Full Auto";
}

function parseTradeJournal(tradesPayload) {
  const header = Array.isArray(tradesPayload.header) ? tradesPayload.header : [];
  const rows = Array.isArray(tradesPayload.trades) ? tradesPayload.trades : [];
  const index = name => header.indexOf(name);
  const columns = {
    timestamp: index("timestamp"),
    pair: index("pair"),
    status: index("status"),
    profit: index("profit"),
    balance: index("balance"),
    action: index("action"),
    ticket: index("ticket"),
  };

  return rows.map(row => ({
    row,
    timestamp: columns.timestamp >= 0 ? row[columns.timestamp] : "",
    pair: columns.pair >= 0 ? row[columns.pair] : "",
    status: columns.status >= 0 ? String(row[columns.status] || "") : "",
    profit: columns.profit >= 0 ? Number(row[columns.profit] || 0) : 0,
    balance: columns.balance >= 0 ? Number(row[columns.balance] || 0) : 0,
  }));
}

function escapeXml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderActivityChart(items) {
  const svg = document.getElementById("activityChart");
  const width = 900;
  const height = 240;
  const padding = 22;
  const innerWidth = width - (padding * 2);
  const innerHeight = height - (padding * 2);
  const closed = items.filter(item => item.status.toUpperCase() === "CLOSE");
  const source = closed.length ? closed : items;
  const values = source.map((item, idx) => {
    if (item.balance) return item.balance;
    return source.slice(0, idx + 1).reduce((sum, current) => sum + current.profit, 0);
  });

  if (!values.length) {
    svg.innerHTML = `<text x="24" y="40" fill="#98adca">No trade activity yet</text>`;
    return;
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = (max - min) || 1;
  const step = source.length > 1 ? innerWidth / (source.length - 1) : innerWidth;

  const points = values.map((value, idx) => {
    const x = padding + (idx * step);
    const y = padding + innerHeight - (((value - min) / span) * innerHeight);
    return { x, y, value };
  });

  const linePath = points.map((point, idx) => `${idx === 0 ? "M" : "L"} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(" ");
  const areaPath = `${linePath} L ${points[points.length - 1].x.toFixed(1)} ${height - padding} L ${points[0].x.toFixed(1)} ${height - padding} Z`;
  const last = points[points.length - 1];
  const first = points[0];
  const labels = [
    { x: padding, y: 18, text: `Start: ${Number(first.value).toFixed(2)}` },
    { x: width - 200, y: 18, text: `Latest: ${Number(last.value).toFixed(2)}` },
  ];

  svg.innerHTML = `
    <defs>
      <linearGradient id="areaFill" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stop-color="#66e9b2" stop-opacity="0.28" />
        <stop offset="100%" stop-color="#66e9b2" stop-opacity="0.02" />
      </linearGradient>
      <linearGradient id="lineStroke" x1="0" x2="1">
        <stop offset="0%" stop-color="#66e9b2" />
        <stop offset="100%" stop-color="#7ea9ff" />
      </linearGradient>
    </defs>
    <rect x="0" y="0" width="${width}" height="${height}" rx="16" fill="rgba(5,10,18,.08)"></rect>
    ${labels.map(label => `<text x="${label.x}" y="${label.y}" fill="#98adca" font-size="12">${escapeXml(label.text)}</text>`).join("")}
    <path d="${areaPath}" fill="url(#areaFill)"></path>
    <path d="${linePath}" fill="none" stroke="url(#lineStroke)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></path>
    ${points.map(point => `<circle cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="3.8" fill="#e7effb"></circle>`).join("")}
  `;
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
  const journal = parseTradeJournal(trades);
  setText("connectionState", connected ? "Connected" : "Disconnected");
  setText("balanceValue", status.account ? `${Number(status.account.balance).toFixed(2)} / ${Number(status.account.equity).toFixed(2)}` : "—");
  setText("positionsValue", String(status.open_positions ?? 0));
  const feedbackCount = model.feedback_samples ?? status.self_learning?.feedback_samples ?? 0;
  setText("mlValue", model.trained ? `Trained (${(model.accuracy * 100).toFixed(1)}%) • ${feedbackCount} feedback` : `Not trained • ${feedbackCount} feedback`);
  setText("pairsValue", Array.isArray(status.pairs) ? status.pairs.join(", ") : "—");
  setText("flagsValue", `Mode: ${modeText(dryRun)}\nLive unlock: ${config.allow_live_trading ? "enabled" : "disabled"}\nAuto retrain: ${config.auto_retrain_enabled ? "enabled" : "disabled"}\nAPI server: ${config.api_enabled ? "enabled" : "disabled"}`);
  const pill = document.getElementById("modePill");
  pill.className = modeClass(dryRun);
  pill.textContent = modeText(dryRun);
  const fullAuto = !!config.full_auto_enabled;
  const autoPill = document.getElementById("autoPill");
  autoPill.className = fullAuto ? "pill ok" : "pill warn";
  autoPill.textContent = autoText(fullAuto);
  setText("modeHeadline", dryRun ? "Demo mode active" : "Live mode active");
  setText("modeDesc", dryRun
    ? "Orders are simulated. Use this to verify signals, pair selection, and tracking without sending live trades."
    : "Live orders are enabled. Keep the bot supervised and confirm the account, broker, and risk settings are correct.");
  const button = document.getElementById("modeButton");
  document.getElementById("modeButtonIcon").textContent = modeButtonIcon(dryRun);
  document.getElementById("modeButtonLabel").textContent = modeButtonText(dryRun);
  button.className = dryRun ? "primary" : "danger";
  button.classList.add("mode-switch");
  button.disabled = false;
  const autoButton = document.getElementById("autoButton");
  autoButton.textContent = autoButtonText(fullAuto);
  autoButton.className = fullAuto ? "primary" : "ghost";
  setNotice(connected ? "Dashboard synced." : "MT5 is disconnected. Check the terminal, account, and credentials.", connected ? "ok" : "warn");
  setText("modeHeadline", fullAuto ? `${dryRun ? "Demo" : "Live"} mode • FULL AUTO` : (dryRun ? "Demo mode active" : "Live mode active"));
  setText("modeDesc", fullAuto
    ? "Full Auto means: Windows startup persistence is enabled, the watchdog restarts the bot after crashes, MT5 reconnect stays on, and scheduled retraining stays on. Use this after a stable demo burn-in and a small live pilot."
    : (dryRun
      ? "Orders are simulated. Use this to verify signals, pair selection, and tracking without sending live trades."
      : "Live orders are enabled. Keep the bot supervised and confirm the account, broker, and risk settings are correct."));

  const closedTrades = journal.filter(item => item.status.toUpperCase() === "CLOSE");
  const closedProfits = closedTrades.map(item => item.profit);
  const wins = closedProfits.filter(value => value > 0).length;
  const today = new Date().toDateString();
  const todayPl = closedTrades.reduce((sum, item) => {
    const stamp = item.timestamp ? new Date(item.timestamp) : null;
    return sum + ((stamp && stamp.toDateString() === today) ? item.profit : 0);
  }, 0);
  setText("todayPl", `${todayPl >= 0 ? "+" : ""}${todayPl.toFixed(2)}`);
  setText("closedTrades", String(closedTrades.length));
  setText("winRate", closedTrades.length ? `${((wins / closedTrades.length) * 100).toFixed(1)}%` : "—");
  setText("openPl", status.account ? `${Number(status.account.profit).toFixed(2)}` : "—");

  renderActivityChart(journal.slice(-24));

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

async function emergencyStop() {
  const proceed = confirm("Emergency stop will stop the scheduler and disconnect MT5. It will not close open positions. Continue?");
  if (!proceed) {
    return;
  }
  const res = await fetch("/emergency-stop", { method: "POST" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    setNotice(data.error || "Emergency stop failed", "bad");
    return;
  }
  setNotice("Emergency stop requested. Refreshing state...", "warn");
  await refresh();
}

async function toggleAutomation() {
  const config = await loadJson("/config");
  const desired = !config.full_auto_enabled;
  const message = desired
    ? "Enable Full Auto? This will create the Windows startup shortcut and keep auto-retrain on."
    : "Disable Full Auto? This will remove the Windows startup shortcut and turn auto-retrain off.";
  const proceed = confirm(message);
  if (!proceed) {
    return;
  }
  const res = await fetch("/automation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled: desired })
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    setNotice(data.error || "Automation update failed", "bad");
    return;
  }
  setNotice(data.message || `Full automatic mode ${desired ? "enabled" : "disabled"}.`, "ok");
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

    def _handle_automation(self):
        bot = self._get_bot()

        try:
            payload = self._read_json_body()
        except Exception:
            self._json({"error": "invalid json"}, 400)
            return

        if not isinstance(payload, dict) or "enabled" not in payload:
            self._json({"error": "enabled field is required"}, 400)
            return

        desired_enabled = bool(payload.get("enabled"))
        current_mode = "live" if not config.DRY_RUN else "dry"

        if desired_enabled and not config.DRY_RUN and not config.ALLOW_LIVE_TRADING:
            self._json({"error": "Live full automation requires ALLOW_LIVE_TRADING=true"}, 403)
            return

        if desired_enabled:
            ok, detail = _run_powershell_script("create_autostart.ps1", ["-Mode", current_mode])
            if not ok:
                self._json({"error": detail or "Failed to create autostart shortcut"}, 500)
                return
        else:
            ok, detail = _run_powershell_script("remove_autostart.ps1", [])
            if not ok:
                self._json({"error": detail or "Failed to remove autostart shortcut"}, 500)
                return

        config.AUTO_RETRAIN_ENABLED = desired_enabled
        shortcut_exists = _startup_shortcut_path().exists()
        get_logger().warning(
            f"Full automatic mode {'enabled' if desired_enabled else 'disabled'} via dashboard "
            f"(mode={current_mode}, shortcut={'present' if shortcut_exists else 'missing'})"
        )

        self._json({
            "ok": True,
            "enabled": desired_enabled,
            "message": "Full automatic mode enabled." if desired_enabled else "Full automatic mode disabled.",
            "autostart_enabled": shortcut_exists,
            "auto_retrain_enabled": config.AUTO_RETRAIN_ENABLED,
        })

    def _handle_emergency_stop(self):
        bot = self._get_bot()
        scheduler = bot.get("scheduler")
        connector = bot.get("connector")
        trade_manager = bot.get("trade_manager")
        stop_event = bot.get("stop_event")

        if trade_manager and hasattr(trade_manager, "write_open_trades_snapshot"):
            try:
                trade_manager.write_open_trades_snapshot()
            except Exception as exc:
                get_logger().warning(f"Emergency stop snapshot failed: {exc}")

        if scheduler and hasattr(scheduler, "stop"):
            try:
                scheduler.stop()
            except Exception as exc:
                get_logger().warning(f"Emergency stop scheduler stop failed: {exc}")

        if connector and hasattr(connector, "disconnect"):
            try:
                connector.disconnect()
            except Exception as exc:
                get_logger().warning(f"Emergency stop disconnect failed: {exc}")

        if stop_event and hasattr(stop_event, "set"):
            try:
                stop_event.set()
            except Exception:
                pass

        get_logger().warning("Emergency stop triggered from dashboard")
        self._json({
            "ok": True,
            "message": "Emergency stop requested. The bot process will exit.",
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
            ML_CONFIDENCE_THRESHOLD, DRY_RUN, ALLOW_LIVE_TRADING, ENABLE_API_SERVER, AUTO_RETRAIN_ENABLED,
        )
        startup_shortcut = _startup_shortcut_path()
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
            "auto_retrain_enabled": AUTO_RETRAIN_ENABLED,
            "autostart_enabled": startup_shortcut.exists(),
            "full_auto_enabled": AUTO_RETRAIN_ENABLED and startup_shortcut.exists(),
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
