param(
    [ValidateSet("live", "dry")]
    [string]$Mode = "live",

    [string[]]$BotArgs = @()
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$launcher = switch ($Mode) {
    "live" { "run_live.ps1" }
    "dry" { "run_dry.ps1" }
}

$powershellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$targetPath = Join-Path $PSScriptRoot $launcher
$arguments = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $targetPath
)
if ($BotArgs) {
    $arguments += $BotArgs
}

Start-Process `
    -FilePath $powershellExe `
    -WindowStyle Hidden `
    -WorkingDirectory $PSScriptRoot `
    -ArgumentList $arguments | Out-Null

Write-Host "Started $Mode mode in the background."
