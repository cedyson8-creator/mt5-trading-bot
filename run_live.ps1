param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$BotArgs
)

$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

. "$PSScriptRoot\launcher_common.ps1"
Invoke-BotLaunch -Mode live -BotArgs $BotArgs
