$ErrorActionPreference = "Stop"

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPython = Join-Path $RootDir ".venv\Scripts\python.exe"

Set-Location $RootDir

if (-not (Test-Path $VenvPython)) {
    & (Join-Path $RootDir "scripts\bootstrap.ps1")
}

& $VenvPython -m codex_usage doctor
& $VenvPython -m compileall codex_usage
& $VenvPython -m unittest discover -s tests

Write-Host "All checks passed."
