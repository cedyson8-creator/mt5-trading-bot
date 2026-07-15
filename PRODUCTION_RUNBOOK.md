# MT5 Trading Bot Production Runbook

This document is the operating procedure for a live deployment.

Use this after:

1. `README.md`
2. `DEPLOYMENT_GUIDE.md`
3. `FINAL_LIVE_CHECKLIST.md`

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

If you want to undo startup persistence:

```powershell
.\remove_autostart.ps1
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

In code:

- `Scheduler` pulls data and requests a decision
- `strategy_engine.generate_signal()` or `MLTradingModel.predict()` creates the signal
- `mtf_filter()` checks the higher-timeframe trend
- `risk_manager` checks spread, SL/TP, size, daily loss, and limits
- `TradeManager.execute_signal()` sends the final order through MT5

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

## 10. Dashboard mode toggle

The local dashboard can switch between demo and live mode at runtime.

- Live mode requires `ALLOW_LIVE_TRADING=true`
- The dashboard should be bound to `127.0.0.1`
- Treat the toggle as an operator convenience, not an excuse to skip preflight

## 11. Full automation mode

This project can run unattended after startup:

- `watchdog.ps1` restarts the bot if it crashes
- `create_autostart.ps1` places a shortcut in the Windows Startup folder
- `remove_autostart.ps1` removes that startup shortcut
- `AUTO_RETRAIN_ENABLED=true` keeps ML retraining scheduled
- the scheduler already reconnects MT5 automatically when the terminal drops

Use this only after a stable demo burn-in and a small live pilot.

## 12. Emergency stop

The dashboard includes an emergency stop button. It:

- writes the open-trades snapshot
- stops the scheduler
- disconnects MT5
- requests process shutdown through the main loop

Use it when you need to stop the bot immediately, then verify open positions directly in MT5.

## 13. Recommended operating rule

Treat this as a supervised trading system, not a fully unattended one. Keep a person responsible for checking it.

## 14. Troubleshooting

If the bot will not start:

- Check MT5 itself first: open the terminal and confirm it is logged in.
- Verify `.env` has valid `MT5_LOGIN`, `MT5_PASSWORD`, and `MT5_SERVER`.
- Run:

```powershell
.\launcher_menu.ps1
```

- Then choose `1` for first run or `4` for live mode.
- Run:

```powershell
.\run_symbols.ps1
python preflight.py --live
```

- If those fail, read `mt5_bot.log`.

If live trading is blocked:

- Confirm `ALLOW_LIVE_TRADING=true`.
- Confirm `DRY_RUN=false`.
- Run:

```powershell
python preflight.py --live
```

- Check that MT5 Algo Trading is enabled.
- Check that the broker server is a live server, not demo.

If the dashboard is unreachable:

- Confirm `ENABLE_API_SERVER=true`.
- Confirm `API_HOST=127.0.0.1`.
- Confirm `API_PORT=8080`.
- Restart the bot with:

```powershell
.\run_live.ps1
```

- Then open `http://127.0.0.1:8080/`

If the bot keeps reconnecting:

- Check the MT5 terminal connection.
- Check internet connectivity.
- Run:

```powershell
.\run_symbols.ps1
```

- Confirm the broker is not down or blocking the account.

If a trade is skipped:

- Check spread in the dashboard or log output.
- Check position limits in `config.py`.
- Check daily loss limits in `config.py`.
- Check broker stop-distance rules in the log.
