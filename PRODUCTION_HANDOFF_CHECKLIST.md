# Production Handoff Checklist

Use this at the machine immediately before live trading.

## Before you start

- [ ] You are on the correct Windows PC
- [ ] The correct GitHub build is installed
- [ ] MT5 is installed and opens normally
- [ ] You are using a dedicated live account
- [ ] You have the account login, password, and broker server name
- [ ] Internet connection is stable

## Configuration

- [ ] `.env` is present and saved
- [ ] `DRY_RUN=false`
- [ ] `ALLOW_LIVE_TRADING=true`
- [ ] `MT5_LOGIN` is correct
- [ ] `MT5_PASSWORD` is correct
- [ ] `MT5_SERVER` is correct
- [ ] `ENABLE_API_SERVER=false` unless you need the dashboard
- [ ] `API_HOST=127.0.0.1`
- [ ] `API_PORT=8080`
- [ ] Symbol basket is correct
- [ ] `pairs.txt` is correct

## MT5 safety

- [ ] Algo trading is enabled
- [ ] Expert Advisors are allowed
- [ ] The broker symbols exist in MT5
- [ ] Lot size, step, and minimum lot are understood
- [ ] Stop distance rules are understood

## Validation

- [ ] `.\run_symbols.ps1` passes
- [ ] `python preflight.py --live` passes
- [ ] `.\run_dry.ps1` passes
- [ ] Dashboard loads at `http://127.0.0.1:8080/` if enabled
- [ ] No unexpected warnings are present

## Recovery and control

- [ ] You know how to stop the bot immediately
- [ ] Emergency stop button works
- [ ] `watchdog.ps1` is configured if you want restart protection
- [ ] `create_autostart.ps1 -Mode live` is configured if you want boot start
- [ ] `remove_autostart.ps1` is available for rollback

## Live launch

- [ ] Start with the smallest practical size
- [ ] Watch the first live trade manually
- [ ] Confirm SL and TP are correct
- [ ] Confirm the journal is logging correctly
- [ ] Confirm the bot is on the expected account

## After launch

- [ ] Open positions match the journal
- [ ] Log file has no repeated order errors
- [ ] Equity and free margin look stable
- [ ] No reconnect loop is happening

If any box is unchecked, do not start live trading.
