# MT5 Trading Bot Production Runbook

This document is the operating procedure for a live deployment.

## 1. Preconditions

- Use a dedicated MT5 account.
- Start in demo mode and verify behavior before live trading.
- Confirm the broker symbols, contract sizes, lot steps, stops levels, and trading hours.
- Keep an external record of account login, server name, and emergency shutdown steps.

## 2. Environment setup

Set the following in `.env`:

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

When you are ready to trade live, change:

```env
ALLOW_LIVE_TRADING=true
```

Leave `ENABLE_API_SERVER=false` unless you specifically need the local status API.
If you need the dashboard, set:

```env
ENABLE_API_SERVER=true
API_HOST=127.0.0.1
API_PORT=8080
```

## 3. Installation

```powershell
.\install_pc.ps1
```

If you want a desktop shortcut:

```powershell
.\create_shortcut.ps1 -Desktop
```

If you want the bot to run without a visible terminal:

```powershell
.\run_background.ps1 -Mode live
```

For crash recovery and boot persistence:

```powershell
.\watchdog.ps1 -Mode live
.\create_autostart.ps1 -Mode live
```

## 4. Preflight before every live launch

Run:

```powershell
.\run_symbols.ps1
.\run_dry.ps1
.\run_live.ps1
```

Or run preflight directly:

```powershell
python preflight.py --live
```

Do not start live trading if preflight fails.

## 5. Go-live checklist

- `ALLOW_LIVE_TRADING=true`
- `DRY_RUN=false`
- Correct `MT5_LOGIN`, `MT5_PASSWORD`, `MT5_SERVER`
- MT5 terminal is logged in and connected
- Algo trading is enabled in MT5
- Symbol basket is correct
- `trade_journal.csv` is writable
- `mt5_bot.log` is writable
- You know how to stop the bot quickly

## 6. Start live trading

```powershell
.\run_live.ps1
```

Monitor:

- the log file
- MT5 open positions
- `trade_journal.csv`
- `open_trades_snapshot.json`

## 7. Daily checks

- Confirm the bot is connected to the expected account.
- Confirm open positions match the journal.
- Check for repeated order failures.
- Check spread conditions and broker trading hours.
- Review equity vs. daily start balance.

## 8. Emergency stop

If anything looks wrong:

1. Stop the bot process.
2. Disable AutoTrading in MT5 if needed.
3. Verify open positions manually in MT5.
4. Preserve logs and journal files for review.

## 9. Rollback

If a new change behaves badly:

1. Revert to the previous Git commit.
2. Reinstall dependencies if the environment changed.
3. Run preflight again.
4. Resume in dry-run first.

## 11. Dashboard mode toggle

The local dashboard can switch between demo and live mode at runtime.

- Live mode requires `ALLOW_LIVE_TRADING=true`
- The dashboard should be bound to `127.0.0.1`
- Treat the toggle as an operator convenience, not an excuse to skip preflight

## 12. Full automation mode

This project can run unattended after startup:

- `watchdog.ps1` restarts the bot if it crashes
- `create_autostart.ps1` places a shortcut in the Windows Startup folder
- `AUTO_RETRAIN_ENABLED=true` keeps ML retraining scheduled
- the scheduler already reconnects MT5 automatically when the terminal drops

Use this only after a stable demo burn-in and a small live pilot.

## 13. Emergency stop

The dashboard includes an emergency stop button. It:

- writes the open-trades snapshot
- stops the scheduler
- disconnects MT5
- requests process shutdown through the main loop

Use it when you need to stop the bot immediately, then verify open positions directly in MT5.

## 10. Recommended operating rule

Treat this as a supervised trading system, not a fully unattended one. Keep a person responsible for checking it.
