param(
    [string]$Python = $env:PYTHON
)

$ErrorActionPreference = "Stop"

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvDir = Join-Path $RootDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

Set-Location $RootDir

$PythonExe = $null
$PythonArgs = @()

if ($Python) {
    $PythonExe = $Python
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonExe = "py"
    $PythonArgs = @("-3")
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PythonExe = "python3"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonExe = "python"
}

if (-not $PythonExe) {
    Write-Error "Python 3 was not found. Install Python 3.9+ and retry."
}

if (-not (Test-Path $VenvPython)) {
    & $PythonExe @PythonArgs -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        throw "Virtual environment creation failed (exit code $LASTEXITCODE)."
    }
}

& $VenvPython -m pip install --upgrade pip | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "pip upgrade failed (exit code $LASTEXITCODE)."
}
& $VenvPython -m pip install -e .
if ($LASTEXITCODE -ne 0) {
    throw "Package installation failed (exit code $LASTEXITCODE)."
}
& $VenvPython -m codex_usage doctor
if ($LASTEXITCODE -ne 0) {
    throw "Runtime check failed (exit code $LASTEXITCODE)."
}

Write-Host ""
Write-Host "Bootstrap complete."
Write-Host ""
Write-Host "Next commands:"
Write-Host "  .\scripts\demo.ps1"
Write-Host "  .\scripts\check.ps1"
Write-Host "  .\.venv\Scripts\codex-usage.exe init"
