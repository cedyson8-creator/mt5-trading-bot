param(
    [ValidateSet("live", "dry")]
    [string]$Mode = "live",

    [int]$RestartDelaySeconds = 10,

    [switch]$RestartOnAnyExit,

    [string[]]$BotArgs = @()
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$powershellExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$launcher = switch ($Mode) {
    "live" { "run_live.ps1" }
    "dry" { "run_dry.ps1" }
}
$targetPath = Join-Path $PSScriptRoot $launcher

Write-Host "Watchdog started for $Mode mode."

while ($true) {
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $targetPath
    )
    if ($BotArgs) {
        $arguments += $BotArgs
    }

    $process = Start-Process `
        -FilePath $powershellExe `
        -WindowStyle Hidden `
        -WorkingDirectory $PSScriptRoot `
        -ArgumentList $arguments `
        -PassThru

    $process.WaitForExit()
    $exitCode = $process.ExitCode

    if (-not $RestartOnAnyExit -and $exitCode -eq 0) {
        Write-Host "Bot exited cleanly. Watchdog stopping."
        break
    }

    Write-Host "Bot exited with code $exitCode. Restarting in $RestartDelaySeconds seconds..."
    Start-Sleep -Seconds $RestartDelaySeconds
}
