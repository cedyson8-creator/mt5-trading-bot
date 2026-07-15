param(
    [string]$ShortcutName = "MT5 Trading Bot Auto"
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$startupDir = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startupDir "$ShortcutName.lnk"

if (Test-Path $shortcutPath) {
    Remove-Item -Force $shortcutPath
    Write-Host "Autostart shortcut removed: $shortcutPath"
} else {
    Write-Host "Autostart shortcut not found: $shortcutPath"
}
