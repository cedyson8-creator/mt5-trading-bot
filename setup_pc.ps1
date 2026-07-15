param(
    [ValidateSet("live", "dry")]
    [string]$Mode = "live",

    [switch]$DesktopShortcut,

    [switch]$EnableAutostart,

    [switch]$ForceRecreateVenv
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$launcherMode = $Mode
$installArgs = @()
if ($ForceRecreateVenv) {
    $installArgs += "-ForceRecreate"
}

Write-Host "Step 1/3: installing Python environment..."
& $PSScriptRoot\install_pc.ps1 @installArgs
if ($LASTEXITCODE -ne 0) {
    throw "Install step failed."
}

Write-Host "Step 2/3: creating launch shortcuts..."
& $PSScriptRoot\create_shortcut.ps1 -Mode $launcherMode
if ($DesktopShortcut) {
    & $PSScriptRoot\create_shortcut.ps1 -Mode $launcherMode -Desktop
}
if ($EnableAutostart) {
    & $PSScriptRoot\create_autostart.ps1 -Mode $launcherMode
}

Write-Host "Step 3/3: setup summary..."
Write-Host "Setup complete for $launcherMode mode."
Write-Host "Next:"
Write-Host "  1. Edit .env with your MT5 credentials."
Write-Host "  2. Run .\run_symbols.ps1 to inspect the basket."
Write-Host "  3. Run .\run_dry.ps1 and preflight before live trading."
if ($EnableAutostart) {
    Write-Host "  4. The Windows Startup shortcut is enabled."
}
if ($DesktopShortcut) {
    Write-Host "  5. A desktop shortcut was created."
}
