$ErrorActionPreference = "Stop"

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPython = Join-Path $RootDir ".venv\Scripts\python.exe"
$Cli = Join-Path $RootDir ".venv\Scripts\codex-usage.exe"

Set-Location $RootDir

if (-not (Test-Path $VenvPython)) {
    & (Join-Path $RootDir "scripts\bootstrap.ps1")
}

$DemoDir = Join-Path ([System.IO.Path]::GetTempPath()) ("codex-usage-demo-" + [System.Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $DemoDir | Out-Null

try {
    @'
<!-- codex-usage:user -->
Can you summarize this tiny repo?

<!-- codex-usage:assistant -->
This repo is a local CLI for estimating Codex subscription usage from visible transcripts.

<!-- codex-usage:tool -->
$ rg --files
README.md
codex_usage/cli.py
'@ | Set-Content -Path (Join-Path $DemoDir "transcript.md") -Encoding UTF8

    Push-Location $DemoDir
    try {
        & $Cli init
        & $Cli group create "demo-run" --label demo
        & $Cli snapshot --group demo-run --usage 10 --note "demo start"
        & $Cli turn add --group demo-run --file transcript.md --task-type simple_chat --requests 1 --tool-calls 1
        & $Cli snapshot --group demo-run --usage 10.2 --note "demo end"
        & $Cli report --group demo-run
        & $Cli export --format csv --output usage.csv
    } finally {
        Pop-Location
    }
} finally {
    Remove-Item -Recurse -Force $DemoDir
}

Write-Host ""
Write-Host "Demo completed in an isolated temporary directory."
