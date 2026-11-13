param([ValidateSet('start','stop','check')][string]$Action='check',[switch]$NoBrowser)
$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$pythonPath=Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
$statePath=Join-Path $projectRoot 'data\service.json'
function Run-Native([string]$exe,[string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) {throw "Command failed: $exe"}
}
function Get-OwnedProcess {
    if (!(Test-Path -LiteralPath $statePath)) {return $null}
    $state=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    $proc=Get-CimInstance Win32_Process -Filter "ProcessId=$($state.pid)" -ErrorAction SilentlyContinue
    if ($proc -and $proc.ExecutablePath -eq $pythonPath -and $proc.CommandLine.Contains('app.main:app') -and $proc.CreationDate.ToUniversalTime().ToString('o') -eq $state.created) {return $proc}
    return $null
}
try {
    if ($Action -eq 'stop') {
        $owned=Get-OwnedProcess
        if ($owned) {
            # Windows venv Python may launch a base-interpreter child. Verify each child.
            $children=Get-CimInstance Win32_Process -Filter "ParentProcessId=$($owned.ProcessId)" | Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine.Contains($pythonPath) -and $_.CommandLine.Contains('app.main:app')}
            foreach ($child in $children) {Stop-Process -Id $child.ProcessId -ErrorAction SilentlyContinue}
            Stop-Process -Id $owned.ProcessId -ErrorAction SilentlyContinue
            Write-Host 'CampusAI stopped.'
        } else {Write-Host 'No verified CampusAI process to stop.'}
        if (Test-Path -LiteralPath $statePath) {Remove-Item -LiteralPath $statePath}
        exit 0
    }
    if (!(Get-Command python -ErrorAction SilentlyContinue)) {throw 'Python 3.11+ required. Install Python and enable Add to PATH.'}
    if (!(Get-Command node -ErrorAction SilentlyContinue)) {throw 'Node.js 20.19+ required. Install Node.js LTS.'}
    Write-Host 'Python / Node:'
    python --version
    node --version
    if ($Action -eq 'start') {
        New-Item -ItemType Directory -Force data,logs,knowledge/uploads | Out-Null
        if (!(Test-Path -LiteralPath '.env')) {Copy-Item -LiteralPath '.env.example' -Destination '.env'}
        $envText=[IO.File]::ReadAllText((Join-Path $projectRoot '.env'))
        if ($envText -notmatch '(?m)^CAMPUSAI_ACCESS_CODE=.+') {
            $accessCode=[Guid]::NewGuid().ToString('N').Substring(0,12)
            if ($envText -match '(?m)^CAMPUSAI_ACCESS_CODE=\s*$') {$envText=[regex]::Replace($envText,'(?m)^CAMPUSAI_ACCESS_CODE=\s*$',"CAMPUSAI_ACCESS_CODE=$accessCode")} else {$envText+="`r`nCAMPUSAI_ACCESS_CODE=$accessCode`r`n"}
            [IO.File]::WriteAllText((Join-Path $projectRoot '.env'),$envText,(New-Object Text.UTF8Encoding $false))
        }
        if (!(Test-Path -LiteralPath $pythonPath)) {Run-Native 'python' @('-m','venv','backend/.venv')}
        & $pythonPath -c 'import fastapi,uvicorn,openai,pypdf,docx,multipart,dotenv,httpx'
        if ($LASTEXITCODE -ne 0) {Run-Native $pythonPath @('-m','pip','install','-r','backend/requirements.txt')}
        Push-Location frontend
        try {
            if (!(Test-Path -LiteralPath 'node_modules')) {Run-Native 'npm.cmd' @('ci')}
            Run-Native 'npm.cmd' @('run','build')
        } finally {Pop-Location}
        $env:PYTHONPATH=Join-Path $projectRoot 'backend'
        Run-Native $pythonPath @('-c','from app.store import init; init()')
        $owned=Get-OwnedProcess
        if (!$owned) {
            $listener=Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
            if ($listener) {throw 'Port 8000 is occupied. No process was stopped. Close the conflicting service or check CampusAI status.'}
            $proc=Start-Process -FilePath $pythonPath -ArgumentList @('-m','uvicorn','app.main:app','--app-dir','backend','--host','0.0.0.0','--port','8000','--no-access-log') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput 'logs/server.log' -RedirectStandardError 'logs/server-error.log'
            Start-Sleep -Milliseconds 700
            $verified=Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.Id)"
            if (!$verified) {throw 'Server exited. See logs/server-error.log.'}
            @{pid=$proc.Id;created=$verified.CreationDate.ToUniversalTime().ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $statePath
        }
        $ready=$false
        for ($i=0;$i -lt 25;$i++) {
            try {$r=Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 2;if($r.app -eq 'CampusAI'){$ready=$true;break}} catch {}
            Start-Sleep -Milliseconds 400
        }
        if (!$ready) {throw 'Health check failed. See logs/server-error.log.'}
        Write-Host "`nCampusAI is ready: http://localhost:8000" -ForegroundColor Green
        if (!$NoBrowser) {Start-Process 'http://localhost:8000'}
    }
    if (Test-Path -LiteralPath '.env') {
        $envText=[IO.File]::ReadAllText((Join-Path $projectRoot '.env'))
        $accessLine=($envText -split "`n" | Where-Object {$_ -match '^CAMPUSAI_ACCESS_CODE='})
        Write-Host "Access code (keep private): $($accessLine -replace '^CAMPUSAI_ACCESS_CODE=','')"
        Write-Host "API key configured: $($envText -match '(?m)^DEEPSEEK_API_KEY=\S+')"
        Write-Host "Model configured: $($envText -match '(?m)^DEEPSEEK_MODEL=\S+')"
    } else {Write-Host '.env missing; start.bat will create it.'}
    if (Test-Path -LiteralPath $pythonPath) {
        $env:PYTHONPATH=Join-Path $projectRoot 'backend'
        Run-Native $pythonPath @('scripts/db_check.py')
    }
    try {$health=Invoke-RestMethod 'http://127.0.0.1:8000/api/health' -TimeoutSec 3;Write-Host "Service: $($health.status)"} catch {Write-Host 'Service: stopped or unreachable'}
    Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*'} | ForEach-Object {Write-Host "LAN candidate: http://$($_.IPAddress):8000"}
    Write-Host 'Use the same trusted Wi-Fi. Firewall client isolation may block phones. Windows settings were not changed.'
} catch {Write-Host $_.Exception.Message -ForegroundColor Red;exit 1}
