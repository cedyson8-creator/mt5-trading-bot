# MT5 Trading Bot

Quick start:

1. Run the installer.
2. Set your MT5 credentials in `.env`.
3. Run preflight.
4. Start the bot.

## Environment

```env
DRY_RUN=false
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=your_live_broker_server
```

## Commands

Install:

```bash
.\install_pc.ps1
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
- Live: `.\run_live.ps1` or `run_live.bat`
- Dry-run: `.\run_dry.ps1` or `run_dry.bat`
- Symbols only: `.\run_symbols.ps1` or `run_symbols.bat`

Branding assets:

- Generate desktop and phone artwork: `.\make_brand_assets.ps1`
- Create a desktop shortcut with the branded icon: `.\create_shortcut.ps1 -Desktop`

## Symbol files

`pairs.txt` can contain one symbol per line or comma-separated symbols. Blank lines and `#` comments are ignored.

## What the bot does

- validates the selected symbols against MT5
- reconciles tracked trades with live positions
- backfills missing closes from MT5 history
- writes `mt5_bot.log`, `trade_journal.csv`, `open_trades_snapshot.json`, `ml_model.pkl`, and `ml_feedback.pkl`

## Safety

- Test with a demo account first.
- Verify symbol names, lot limits, and broker stop rules.
- Confirm automated trading is enabled in MT5 before going live.
