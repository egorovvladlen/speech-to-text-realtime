$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$PidPath = Join-Path $Root ".translator.pid"

if (!(Test-Path $PidPath)) {
    Write-Host "Service PID file not found. It may already be stopped."
    exit 0
}

$PidText = (Get-Content $PidPath | Select-Object -First 1).Trim()
if ($PidText -notmatch '^\d+$') {
    Write-Host "Invalid PID file."
    exit 1
}

$ServicePid = [int]$PidText
$Process = Get-Process -Id $ServicePid -ErrorAction SilentlyContinue
if ($null -eq $Process) {
    Remove-Item $PidPath -Force
    Write-Host "Service was not running. Removed stale PID file."
    exit 0
}

if ($Process.ProcessName -notin @("python", "pythonw")) {
    Write-Host "PID belongs to a non-Python process. Remove .translator.pid manually if needed."
    exit 1
}

Stop-Process -Id $ServicePid -Force
Remove-Item $PidPath -Force
Write-Host "Service stopped."
