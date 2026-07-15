function Invoke-BotLaunch {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("live", "dry")]
        [string]$Mode,

        [Parameter()]
        [string[]]$BotArgs = @()
    )

    $pythonExe = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (-not (Test-Path $pythonExe)) {
        $pythonExe = "python"
    }

    $modeFlag = if ($Mode -eq "live") { "--live" } else { "--dry-run" }

    Write-Host "Running preflight check..."
    & $pythonExe preflight.py $modeFlag @BotArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Preflight failed. $Mode trading will not start." -ForegroundColor Red
        exit $LASTEXITCODE
    }

    Write-Host "Preflight passed. Starting bot in $Mode mode..."
    & $pythonExe main.py $modeFlag @BotArgs
    exit $LASTEXITCODE
}
