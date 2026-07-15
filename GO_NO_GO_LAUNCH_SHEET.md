# Go / No-Go Launch Sheet

Use this immediately before pressing live.

## Go only if all are true

- [ ] Correct Windows PC
- [ ] Correct GitHub build installed
- [ ] MT5 opens and is logged into the live account
- [ ] `MT5_LOGIN`, `MT5_PASSWORD`, and `MT5_SERVER` are correct
- [ ] `MT5_SERVER` is a live server, not demo
- [ ] `DRY_RUN=false`
- [ ] `ALLOW_LIVE_TRADING=true`
- [ ] `ENABLE_API_SERVER=false` unless you need the dashboard
- [ ] Dashboard, if enabled, is on `http://127.0.0.1:8080/`
- [ ] `pairs.txt` contains only `EURUSD`, `GBPUSD`, and `USDJPY`
- [ ] `.\run_symbols.ps1` passed
- [ ] `python preflight.py --live` passed
- [ ] `.\run_dry.ps1` passed
- [ ] Algo trading is enabled in MT5
- [ ] You know how to stop the bot immediately
- [ ] Emergency stop works
- [ ] You are ready to watch the first live trade manually

## No-Go if any are true

- [ ] Any validation failed
- [ ] Symbol basket is wrong
- [ ] MT5 is on a demo account
- [ ] `ALLOW_LIVE_TRADING` is still false
- [ ] The dashboard is exposed anywhere other than localhost
- [ ] You cannot confirm the broker server is live

If any No-Go item is true, do not start live trading.
