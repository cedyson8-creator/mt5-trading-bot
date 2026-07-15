# MT5 Trading Bot

Quick start:

1. Run the installer.
2. Set your MT5 credentials in `.env`.
3. Run preflight.
4. Start the bot.

## Environment

```env
DRY_RUN=false
ALLOW_LIVE_TRADING=false
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=your_live_broker_server
ENABLE_API_SERVER=false
API_HOST=127.0.0.1
API_PORT=8080
```

## Commands

Install:

```bash
.\install_pc.ps1
```

One-step setup:

```bash
.\setup_pc.ps1 -Mode live -DesktopShortcut -EnableAutostart
```

First run:

```bash
.\first_run.ps1
```

Launcher menu:

```bash
.\launcher_menu.ps1
```

Preflight:

```bash
python preflight.py --live
```

Live:

```bash
python main.py --live
```

Useful options:

- `--dry-run` or `--live`
- `--pair EURUSD` or repeat `--pair`
- `--pairs EURUSD,GBPUSD`
- `--pairs-file pairs.txt`
- `--strict-symbols`
- `--list-symbols`

Examples:

```bash
python preflight.py --live --pairs-file pairs.txt
python main.py --live --pairs EURUSD,GBPUSD
python main.py --list-symbols --pairs-file pairs.txt
```

Launchers:

- Install: `.\install_pc.ps1` or `install_pc.bat`
- Setup: `.\setup_pc.ps1` or `setup_pc.bat`
- First run: `.\first_run.ps1` or `first_run.bat`
- Menu: `.\launcher_menu.ps1` or `launcher_menu.bat`
- Live: `.\run_live.ps1` or `run_live.bat`
- Dry-run: `.\run_dry.ps1` or `run_dry.bat`
- Background: `.\run_background.ps1 -Mode live` or `run_background.bat live`
- Watchdog: `.\watchdog.ps1 -Mode live` or `watchdog.bat live`
- Autostart: `.\create_autostart.ps1 -Mode live`
- Symbols only: `.\run_symbols.ps1` or `run_symbols.bat`

Branding assets:

- Generate desktop and phone artwork: `.\make_brand_assets.ps1`
- Create a desktop shortcut with the branded icon: `.\create_shortcut.ps1 -Desktop`

Production:

- Read `PRODUCTION_RUNBOOK.md` before going live.
- Read `DEPLOYMENT_GUIDE.md` for Windows setup and packaging.
- Read `FINAL_LIVE_CHECKLIST.md` before the first live trade.
- If you enable the API server, open `http://127.0.0.1:8080/` in a browser to use the dashboard and mode toggle.
- The dashboard now includes live KPI tiles, a trade activity chart, and an emergency stop button.
- For fully automatic startup and crash recovery, use the watchdog launcher and autostart shortcut.
- The dashboard also has a Full Auto switch that creates or removes the Windows startup shortcut and keeps auto-retraining on or off.

## Symbol files

`pairs.txt` can contain one symbol per line or comma-separated symbols. Blank lines and `#` comments are ignored.

## What the bot does

- validates the selected symbols against MT5
- reconciles tracked trades with live positions
- backfills missing closes from MT5 history
- writes `mt5_bot.log`, `trade_journal.csv`, `open_trades_snapshot.json`, `ml_model.pkl`, and `ml_feedback.pkl`

## Trading flow

```text
Market data
   ↓
Signal step
   ↓
ML confirmation
   ↓
Trend filter
   ↓
Risk checks
   ↓
Place trade
```

In code, that maps roughly to:

- `Scheduler` pulls data and requests a decision
- `strategy_engine.generate_signal()` or `MLTradingModel.predict()` creates the signal
- `mtf_filter()` checks the higher-timeframe trend
- `risk_manager` checks spread, SL/TP, size, daily loss, and limits
- `TradeManager.execute_signal()` sends the final order through MT5

Rule of thumb:

- signal says what to do
- ML says how confident it is
- risk decides whether the trade is allowed

## Safety

- Test with a demo account first.
- Verify symbol names, lot limits, and broker stop rules.
- Set `ALLOW_LIVE_TRADING=true` only when you intentionally want live orders enabled.
- Keep the API server disabled unless you explicitly need it, and bind it to `127.0.0.1`.
- Confirm automated trading is enabled in MT5 before going live.
