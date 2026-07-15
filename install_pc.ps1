param(
    [switch]$ForceRecreate
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$pythonExe = (Get-Command python -ErrorAction Stop).Source
$venvPath = Join-Path $PSScriptRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

if ($ForceRecreate -and (Test-Path $venvPath)) {
    Remove-Item -Recurse -Force $venvPath
}

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment..."
    & $pythonExe -m venv .venv
}

Write-Host "Upgrading pip..."
& $venvPython -m pip install --upgrade pip

Write-Host "Installing requirements..."
& $venvPython -m pip install -r requirements.txt

Write-Host ""
Write-Host "Install complete."
Write-Host "Next:"
Write-Host "  1. Edit .env with your MT5 credentials."
Write-Host "  2. Set ALLOW_LIVE_TRADING=true only when you are ready to trade live."
Write-Host "  3. Run .\run_symbols.ps1 to inspect the basket."
Write-Host "  4. Run .\run_live.ps1 or .\run_dry.ps1."
Write-Host "  5. For automatic startup, run .\create_autostart.ps1 -Mode live."
