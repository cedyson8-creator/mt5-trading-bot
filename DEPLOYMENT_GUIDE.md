# Windows Deployment Guide

This is the clean deployment path for a fresh Windows PC.

## Option 1: Manual deployment

1. Copy the repo to the target machine.
2. Open PowerShell in the project folder.
3. Run:

```powershell
.\install_pc.ps1
```

4. Edit `.env`.
5. Run:

```powershell
.\run_symbols.ps1
python preflight.py --live
.\run_dry.ps1
```

6. If everything is correct, run:

```powershell
.\run_live.ps1
```

## Option 2: One-step setup

If you want the script to install Python packages and create launch shortcuts in one pass:

```powershell
.\setup_pc.ps1 -Mode live -DesktopShortcut -EnableAutostart
```

Then edit `.env` and run the checklist.

## Option 3: Guided first run

If this is a fresh PC and you want the bot to walk you through the basics:

```powershell
.\first_run.ps1
```

It will install, list symbols, and run demo preflight before telling you what to do next.

## Option 4: Launcher menu

If you want a simple interactive menu:

```powershell
.\launcher_menu.ps1
```

## Option 5: Release package

1. On the build machine, run:

```powershell
.\package_windows.ps1
```

2. Copy `dist\mt5-trading-bot-release.zip` to the target PC.
3. Unzip it.
4. Run `install_pc.ps1`.
5. Follow `FINAL_LIVE_CHECKLIST.md`.

## Recommended production setup

- Use a dedicated Windows user account
- Keep the bot in its own folder
- Use the watchdog for crash recovery
- Use autostart only after demo burn-in
- Keep the dashboard bound to localhost

## Rollback

If something goes wrong:

1. Stop the bot.
2. Remove the autostart shortcut.
3. Run demo mode again.
4. Recheck the checklist before relaunching live.

## Troubleshooting

If install fails:

```powershell
python --version
.\install_pc.ps1 -ForceRecreate
```

If the bot does not start:

```powershell
.\launcher_menu.ps1
.\run_symbols.ps1
python preflight.py --live
```

If the dashboard does not open:

```powershell
.\run_live.ps1
```

Then verify:

- `ENABLE_API_SERVER=true`
- `API_HOST=127.0.0.1`
- `API_PORT=8080`

If autostart is wrong:

```powershell
.\remove_autostart.ps1
.\create_autostart.ps1 -Mode live
```

If you need to rebuild the release package:

```powershell
.\package_windows.ps1
```
