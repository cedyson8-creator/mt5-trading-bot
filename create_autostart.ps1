param(
    [ValidateSet("live", "dry")]
    [string]$Mode = "live",

    [string]$ShortcutName = "MT5 Trading Bot Auto"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$startupDir = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir "$ShortcutName.lnk"
$powershellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$targetPath = Join-Path $PSScriptRoot "watchdog.ps1"
$iconPath = Join-Path $PSScriptRoot "assets\brand\mt5-bot-icon.ico"

$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $powershellExe
$shortcut.Arguments = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$targetPath`" -Mode $Mode"
$shortcut.WorkingDirectory = $PSScriptRoot
if (Test-Path $iconPath) {
    $shortcut.IconLocation = $iconPath
} else {
    $shortcut.IconLocation = "$powershellExe,0"
}
$shortcut.Description = "MT5 Trading Bot Auto Start ($Mode)"
$shortcut.Save()

Write-Host "Autostart shortcut created: $shortcutPath"
