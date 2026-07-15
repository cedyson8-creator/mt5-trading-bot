# Final Live Trading Checklist

Use this checklist immediately before turning on real trading.

## Machine and account

- [ ] Dedicated Windows machine is ready
- [ ] MT5 is installed and opens normally
- [ ] Correct live MT5 account credentials are set
- [ ] `MT5_LOGIN`, `MT5_PASSWORD`, and `MT5_SERVER` are correct
- [ ] The account is a live account, not demo
- [ ] Internet connection is stable

## Bot configuration

- [ ] `.env` exists and is saved
- [ ] `DRY_RUN=false`
- [ ] `ALLOW_LIVE_TRADING=true`
- [ ] `ENABLE_API_SERVER=true` only if you want the dashboard
- [ ] `API_HOST=127.0.0.1`
- [ ] `AUTO_RETRAIN_ENABLED=true` only if you want full automation
- [ ] Symbol basket is correct
- [ ] `pairs.txt` matches what you expect

## MT5 safety settings

- [ ] Algo trading is enabled in MT5
- [ ] Expert Advisors are allowed
- [ ] Symbol names are valid for this broker
- [ ] Lot step, minimum lot, and maximum lot are understood
- [ ] Stop distance rules are understood

## Dry-run validation

- [ ] `.\run_symbols.ps1` passes
- [ ] `python preflight.py --live` passes
- [ ] `.\run_dry.ps1` runs without errors
- [ ] Dashboard loads at `http://127.0.0.1:8080/` if enabled
- [ ] No unexpected warnings are shown

## Safety and recovery

- [ ] You know how to stop the bot quickly
- [ ] Emergency stop button works
- [ ] `watchdog.ps1` is configured if you want auto-restart
- [ ] `create_autostart.ps1 -Mode live` has been run if you want boot startup
- [ ] `remove_autostart.ps1` is available for rollback

## Live launch

- [ ] Start with small size or minimal risk
- [ ] Watch the first live trade manually
- [ ] Confirm the first order has the expected SL and TP
- [ ] Confirm the journal is logging correctly
- [ ] Confirm the bot is on the expected account

## After launch

- [ ] Check open positions after the first cycle
- [ ] Check the log file for order errors
- [ ] Confirm equity and free margin are stable
- [ ] Confirm no repeated reconnect loops

If any box is unchecked, do not start live trading.
