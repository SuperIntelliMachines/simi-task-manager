# PowerShell healthcheck for SIMI Task Manager foundation
# Run: powershell -ExecutionPolicy Bypass -File .\healthcheck.ps1

Write-Host "\n== SIMI Task Manager Healthcheck ==\n"

function Check-Step {
    param(
        [string]$Label,
        [scriptblock]$Command
    )
    try {
        & $Command
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[PASS] $Label" -ForegroundColor Green
        } else {
            Write-Host "[FAIL] $Label (exit $LASTEXITCODE)" -ForegroundColor Red
        }
    } catch {
        Write-Host "[FAIL] $Label ($_)" -ForegroundColor Red
    }
}

# 1. Docker Compose services
Check-Step "Docker Compose up" { docker compose -f docker-compose.dev.yml up -d --build }
Check-Step "Docker Compose ps" { docker compose -f docker-compose.dev.yml ps }

# 2. Health endpoints
Start-Sleep -Seconds 5
Check-Step "/healthz endpoint" { curl -s http://localhost:8000/healthz | Select-String 'ok' }
Check-Step "/readyz endpoint" { curl -s http://localhost:8000/readyz | Select-String 'ready' }

# 3. Backend checks
Check-Step "Backend pytest" { cd backend; python -m pytest tests/ -v; cd .. }
Check-Step "Backend ruff" { cd backend; ruff check app tests; cd .. }
Check-Step "Backend mypy" { cd backend; mypy app; cd .. }

# 4. Frontend checks
Check-Step "Frontend lint" { cd frontend; npm run lint; cd .. }
Check-Step "Frontend typecheck" { cd frontend; npm run typecheck; cd .. }
Check-Step "Frontend test" { cd frontend; npm run test; cd .. }
Check-Step "Frontend build" { cd frontend; npm run build; cd .. }

Write-Host "\n== Healthcheck Complete ==\n"