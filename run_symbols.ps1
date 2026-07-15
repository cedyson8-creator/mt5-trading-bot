param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$BotArgs
)

$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

& python preflight.py --list-symbols @BotArgs
exit $LASTEXITCODE
