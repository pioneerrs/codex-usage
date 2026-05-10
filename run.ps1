$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path

& (Join-Path $RootDir "scripts\bootstrap.ps1")
& (Join-Path $RootDir "scripts\demo.ps1")
