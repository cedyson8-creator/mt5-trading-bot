param(
    [string]$OutputDir = (Join-Path $PSScriptRoot "dist"),
    [string]$PackageName = "mt5-trading-bot-release"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$releaseRoot = Join-Path $OutputDir $PackageName
$archivePath = Join-Path $OutputDir "$PackageName.zip"

$includeFiles = @(
    "README.md",
    "PRODUCTION_RUNBOOK.md",
    "FINAL_LIVE_CHECKLIST.md",
    "requirements.txt",
    "config.py",
    "main.py",
    "preflight.py",
    "api_server.py",
    "scheduler.py",
    "trade_manager.py",
    "trade_persistence.py",
    "startup_checks.py",
    "mt5_connector.py",
    "risk_manager.py",
    "strategy_engine.py",
    "ml_model.py",
    "logger.py",
    "notifier.py",
    "runtime_options.py",
    "pair_utils.py",
    "install_pc.ps1",
    "install_pc.bat",
    "setup_pc.ps1",
    "setup_pc.bat",
    "first_run.ps1",
    "first_run.bat",
    "launcher_menu.ps1",
    "launcher_menu.bat",
    "launcher_common.ps1",
    "run_live.ps1",
    "run_live.bat",
    "run_dry.ps1",
    "run_dry.bat",
    "run_symbols.ps1",
    "run_symbols.bat",
    "run_background.ps1",
    "run_background.bat",
    "watchdog.ps1",
    "watchdog.bat",
    "create_shortcut.ps1",
    "create_shortcut.bat",
    "create_autostart.ps1",
    "create_autostart.bat",
    "remove_autostart.ps1",
    "remove_autostart.bat",
    "make_brand_assets.ps1",
    "pairs.txt"
)

$includeDirs = @(
    "assets\brand",
    "backtest"
)

if (Test-Path $releaseRoot) {
    Remove-Item -Recurse -Force $releaseRoot
}

New-Item -ItemType Directory -Force -Path $releaseRoot | Out-Null

foreach ($file in $includeFiles) {
    $source = Join-Path $PSScriptRoot $file
    if (Test-Path $source) {
        $dest = Join-Path $releaseRoot $file
        $destDir = Split-Path $dest -Parent
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        Copy-Item -Force $source $dest
    }
}

foreach ($dir in $includeDirs) {
    $sourceDir = Join-Path $PSScriptRoot $dir
    if (Test-Path $sourceDir) {
        $destDir = Join-Path $releaseRoot $dir
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        Copy-Item -Recurse -Force (Join-Path $sourceDir "*") $destDir
    }
}

@"
MT5 Trading Bot Release Package

Contents:
- Python sources and Windows launchers
- Branding assets
- Production docs and checklist

Setup:
1. Unzip this folder on the target PC.
2. Run install_pc.ps1.
3. Configure .env.
4. Use run_dry.ps1 and preflight.py before live trading.
"@ | Set-Content -Encoding UTF8 (Join-Path $releaseRoot "PACKAGE_README.txt")

if (Test-Path $archivePath) {
    Remove-Item -Force $archivePath
}

Compress-Archive -Path (Join-Path $releaseRoot "*") -DestinationPath $archivePath

Write-Host "Release folder: $releaseRoot"
Write-Host "Archive: $archivePath"
