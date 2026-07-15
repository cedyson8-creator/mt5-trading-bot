param(
    [ValidateSet("live", "dry", "symbols")]
    [string]$Mode = "live",

    [string]$ShortcutName = "MT5 Trading Bot",

    [switch]$Desktop
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$targetScript = switch ($Mode) {
    "live" { "run_live.ps1" }
    "dry" { "run_dry.ps1" }
    "symbols" { "run_symbols.ps1" }
}

$shortcutDir = if ($Desktop) {
    [Environment]::GetFolderPath("Desktop")
} else {
    $PSScriptRoot
}

$shortcutPath = Join-Path $shortcutDir "$ShortcutName.lnk"
$powershellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$targetPath = Join-Path $PSScriptRoot $targetScript
$iconPath = Join-Path $PSScriptRoot "assets\brand\mt5-bot-icon.ico"

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $powershellExe
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$targetPath`""
$shortcut.WorkingDirectory = $PSScriptRoot
if (Test-Path $iconPath) {
    $shortcut.IconLocation = $iconPath
} else {
    $shortcut.IconLocation = "$powershellExe,0"
}
$shortcut.Description = "MT5 Trading Bot ($Mode)"
$shortcut.Save()

Write-Host "Shortcut created: $shortcutPath"
