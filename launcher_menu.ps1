param(
    [switch]$EnableAutostart,
    [switch]$DesktopShortcut
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$powershellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"

function Pause-Menu {
    Read-Host "Press Enter to continue"
}

function Invoke-MenuScript {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Script,

        [string[]]$Args = @(),

        [switch]$Background
    )

    $path = Join-Path $PSScriptRoot $Script
    if (-not (Test-Path $path)) {
        Write-Host "Missing script: $Script" -ForegroundColor Red
        return
    }

    if ($Background) {
        $arguments = @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", $path
        )
        if ($Args) {
            $arguments += $Args
        }
        Start-Process -FilePath $powershellExe -WindowStyle Hidden -WorkingDirectory $PSScriptRoot -ArgumentList $arguments | Out-Null
        Write-Host "Started $Script in the background."
        return
    }

    & $path @Args
}

function Open-Dashboard {
    $url = "http://127.0.0.1:8080/"
    Start-Process $url
    Write-Host "Opened dashboard: $url"
}

function Show-Menu {
    Clear-Host
    Write-Host "MT5 Trading Bot Launcher" -ForegroundColor Cyan
    Write-Host "--------------------------------"
    Write-Host "1. First run (install + demo preflight)"
    Write-Host "2. Setup PC (install + shortcuts)"
    Write-Host "3. Run demo mode"
    Write-Host "4. Run live mode"
    Write-Host "5. Run live in background"
    Write-Host "6. Create desktop shortcut"
    Write-Host "7. Enable autostart"
    Write-Host "8. Remove autostart"
    Write-Host "9. Package release"
    Write-Host "10. Open dashboard hint"
    Write-Host "11. Open dashboard"
    Write-Host "0. Exit"
    Write-Host ""
}

while ($true) {
    Show-Menu
    $choice = Read-Host "Choose"

    switch ($choice) {
        "1" {
            Invoke-MenuScript -Script "first_run.ps1" -Args @("-Mode", "dry")
            Pause-Menu
        }
        "2" {
            $args = @("-Mode", "live")
            if ($DesktopShortcut) { $args += "-DesktopShortcut" }
            if ($EnableAutostart) { $args += "-EnableAutostart" }
            Invoke-MenuScript -Script "setup_pc.ps1" -Args $args
            Pause-Menu
        }
        "3" {
            Invoke-MenuScript -Script "run_dry.ps1" -Background
            Pause-Menu
        }
        "4" {
            Invoke-MenuScript -Script "run_live.ps1" -Background
            Pause-Menu
        }
        "5" {
            Invoke-MenuScript -Script "run_background.ps1" -Args @("-Mode", "live")
            Pause-Menu
        }
        "6" {
            Invoke-MenuScript -Script "create_shortcut.ps1" -Args @("-Mode", "live", "-Desktop")
            Pause-Menu
        }
        "7" {
            Invoke-MenuScript -Script "create_autostart.ps1" -Args @("-Mode", "live")
            Pause-Menu
        }
        "8" {
            Invoke-MenuScript -Script "remove_autostart.ps1"
            Pause-Menu
        }
        "9" {
            Invoke-MenuScript -Script "package_windows.ps1"
            Pause-Menu
        }
        "10" {
            Write-Host "If ENABLE_API_SERVER=true, open http://127.0.0.1:8080/ in your browser."
            Pause-Menu
        }
        "11" {
            Open-Dashboard
            Pause-Menu
        }
        "0" { break }
        default {
            Write-Host "Invalid choice." -ForegroundColor Yellow
            Pause-Menu
        }
    }
}
