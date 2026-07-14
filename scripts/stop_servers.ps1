<#
Stop-Servers: checks ports 8000 and 5173 and stops owning processes.

Usage:
  # interactive (asks before killing each PID)
  powershell -ExecutionPolicy Bypass -File .\scripts\stop_servers.ps1

  # non-interactive (auto confirm)
  powershell -ExecutionPolicy Bypass -File .\scripts\stop_servers.ps1 -AutoConfirm
#>

param(
    [switch]$AutoConfirm
)

$ports = @(8000, 5173)

foreach ($port in $ports) {
    Write-Host "\nChecking port $port..." -ForegroundColor Cyan
    $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' }
    if (-not $conns) {
        Write-Host "  No listener on port $port" -ForegroundColor Green
        continue
    }

    $ownPids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($ownPid in $ownPids) {
        if (-not $ownPid) { continue }
        Write-Host "  Port $port -> PID $ownPid" -ForegroundColor Yellow
        try {
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $ownPid" -ErrorAction Stop
            Write-Host "    CommandLine: $($proc.CommandLine)"
        } catch {
            Write-Host "    Process $ownPid not found or inaccessible" -ForegroundColor Red
        }

        $doKill = $false
        if ($AutoConfirm) { $doKill = $true } else {
            $ans = Read-Host "    Stop process $ownPid? (y/N)"
            if ($ans -match '^[Yy]') { $doKill = $true }
        }

        if ($doKill) {
            try {
                Stop-Process -Id $ownPid -Force -ErrorAction Stop
                Write-Host "    Stopped $ownPid" -ForegroundColor Green
            } catch {
                $errMsg = $_.Exception.Message
                Write-Host ("    Failed to stop {0}: {1}" -f $ownPid, $errMsg) -ForegroundColor Red
            }
        } else {
            Write-Host "    Skipped $ownPid" -ForegroundColor DarkYellow
        }
    }
}

Write-Host "\nDone." -ForegroundColor Cyan
