param(
    [ValidateSet("live", "dry")]
    [string]$Mode = "dry",

    [switch]$DesktopShortcut,

    [switch]$EnableAutostart,

    [switch]$ForceRecreateVenv,

    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "First run setup starting..."

if (-not $SkipInstall) {
    $setupArgs = @(
        "-Mode", $Mode
    )
    if ($DesktopShortcut) {
        $setupArgs += "-DesktopShortcut"
    }
    if ($EnableAutostart) {
        $setupArgs += "-EnableAutostart"
    }
    if ($ForceRecreateVenv) {
        $setupArgs += "-ForceRecreateVenv"
    }

    & $PSScriptRoot\setup_pc.ps1 @setupArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Setup step failed."
    }
} else {
    Write-Host "Skipping install/setup step."
}

Write-Host ""
Write-Host "Step 2/4: listing symbols..."
& $PSScriptRoot\run_symbols.ps1
if ($LASTEXITCODE -ne 0) {
    throw "Symbol listing failed."
}

Write-Host ""
Write-Host "Step 3/4: running demo preflight..."
& $PSScriptRoot\preflight.py --dry-run
if ($LASTEXITCODE -ne 0) {
    throw "Demo preflight failed."
}

Write-Host ""
Write-Host "Step 4/4: ready for next action."
Write-Host "If you have already completed demo burn-in, run:"
Write-Host "  .\run_live.ps1"
Write-Host "Otherwise run:"
Write-Host "  .\run_dry.ps1"
